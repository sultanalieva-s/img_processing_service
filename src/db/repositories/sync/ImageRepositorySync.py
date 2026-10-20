import uuid

from sqlalchemy.orm import Session

from src.db.models.image_models import Image


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
