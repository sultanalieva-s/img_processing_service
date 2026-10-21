import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.image_models import Image


class ImageRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self, image_id: uuid.UUID) -> Image | None:
        """Return an image by id, or None if it doesn't exist."""
        stmt = select(Image).where(Image.id == image_id)
        return await self._session.scalar(stmt)

    async def get_all(self, *, limit: int = 20, offset: int = 0) -> list[Image]:
        """Return a page of images, newest first, each with its thumbnails."""
        stmt = (
            select(Image)
            .options(selectinload(Image.thumbnails))
            # id as a tie-breaker keeps pagination stable for equal timestamps
            .order_by(Image.created_at.desc(), Image.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def count(self):
        return await self._session.scalar(select(func.count()).select_from(Image)) or 0
