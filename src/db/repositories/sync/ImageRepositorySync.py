import uuid

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.db.models.image_models import Image, ImageThumbnail


class ImageRepositorySync:
    """ a synchronous image repository"""

    def __init__(self, session: Session):
        self._session = session

    def create(
        self,
        *,
        image_id: uuid.UUID,
        original_filename: str,
        content_type: str,
        size_bytes: int,
        width: int,
        height: int,
        storage_key: str,
    ) -> uuid.UUID:
        image = Image(
            id=image_id,
            original_filename=original_filename,
            content_type=content_type,
            size_bytes=size_bytes,
            width=width,
            height=height,
            storage_key=storage_key,
        )
        self._session.add(image)
        try:
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return image_id

    def get(self, image_id: uuid.UUID) -> Image | None:
        stmt = select(Image).where(Image.id == image_id)
        return self._session.scalar(stmt)

    def upsert_thumbnail(
            self,
            *,
            image_id: uuid.UUID,
            name: str,
            format: str,
            width: int,
            height: int,
            size_bytes: int,
            storage_key: str,
    ) -> None:
        stmt = insert(ImageThumbnail).values(
            image_id=image_id,
            name=name,
            format=format,
            width=width,
            height=height,
            size_bytes=size_bytes,
            storage_key=storage_key,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_image_thumbnail_name",
            set_={
                "format": stmt.excluded.format,
                "width": stmt.excluded.width,
                "height": stmt.excluded.height,
                "size_bytes": stmt.excluded.size_bytes,
                "storage_key": stmt.excluded.storage_key,
                "updated_at": func.now(),
            },
        )
        try:
            self._session.execute(stmt)
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
