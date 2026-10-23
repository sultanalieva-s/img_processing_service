import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.db.models.image_models import Image, ImageThumbnail


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

    async def get_thumbnail(self, image_id: uuid.UUID, name: str) -> ImageThumbnail | None:
        stmt = select(ImageThumbnail).where(
            ImageThumbnail.image_id == image_id,
            ImageThumbnail.name == name,
        )
        return await self._session.scalar(stmt)

    async def get_thumbnails(self, image_id: uuid.UUID) -> list[ImageThumbnail] | None:
        stmt = select(ImageThumbnail).where(ImageThumbnail.image_id == image_id)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def get_thumbnails_by_name(
            self, name: str, *, limit: int, offset: int
    ) -> list[ImageThumbnail]:
        stmt = (
            select(ImageThumbnail)
            .join(Image, Image.id == ImageThumbnail.image_id)
            .where(ImageThumbnail.name == name)
            .order_by(Image.created_at.desc(), ImageThumbnail.id.desc())
            .limit(limit)
            .offset(offset)
        )
        return list((await self._session.scalars(stmt)).all())

    async def count_thumbnails(self, name: str) -> int:
        stmt = select(func.count()).select_from(ImageThumbnail).where(ImageThumbnail.name == name)
        return await self._session.scalar(stmt) or 0
