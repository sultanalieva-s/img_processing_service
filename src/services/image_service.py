import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from src.celery_tasks import process_image
from src.db.models.image_models import Image
from src.db.repositories.asynch.image_repository import ImageRepository

from src.utils.image_validations import validate_image
from src.storage.local_storage import LocalStorage


@dataclass(frozen=True)
class StoredFile:
    path: Path
    media_type: str
    filename: str


def _clean_filename(name: str | None) -> str:
    """Keep the client's filename for display only: no folders, bounded length."""
    name = (name or "").replace("\x00", "").replace("\\", "/").split("/")[-1].strip()
    return name[:255] or "unnamed"



class ImageService:
    """asynchronous image service. (uses async repository) """

    def __init__(self, repo: ImageRepository, storage: LocalStorage):
        self._repo = repo
        self._storage = storage

    async def get(self, image_id: uuid.UUID)-> Image | None:
        return await self._repo.get(image_id)

    async def get_all(self, *, lim: int = 20, off: int = 0)-> tuple[list[Image], int]:
        images = await self._repo.get_all(limit=lim, offset=off)
        total = await self._repo.count()
        return images, total

    async def get_img_file(self, image_id: uuid.UUID) -> StoredFile | None:
        image = await self._repo.get(image_id)
        if image is None:
            return None
        return self._locate(image.storage_key, image.content_type, image.original_filename)

    def _locate(self, key: str, media_type: str, filename: str) -> StoredFile | None:
        path = self._storage.path(key)
        if not path.is_file():      # row exists but the file is gone
            return None
        return StoredFile(path, media_type, filename)


class ImageServiceSync:
    """Image service that uses a sync repository."""

    def __init__(self, repo, storage: LocalStorage):
        self._repo = repo
        self._storage = storage

    def upload(self, file: UploadFile) -> str:
        # 1. Validate. Raises ImageValidationError subclasses on bad input.
        meta = validate_image(file.file)

        # 2. Build the storage key ourselves; the filename is never used in a path.
        image_id = uuid.uuid4()
        key = f"images/{image_id}/original.{meta.extension}"

        # 3. File first, then the DB row.
        self._storage.save(key, file.file)

        try:
            self._repo.create(
                image_id=image_id,
                original_filename=_clean_filename(file.filename),
                content_type=meta.content_type,
                size_bytes=meta.size_bytes,
                width=meta.width,
                height=meta.height,
                storage_key=key,
            )
        except Exception:
            # no orphan files if the insert fails
            self._storage.delete_prefix(f"images/{image_id}")
            raise

        # enqueue a celery task:
        process_image.delay(image_id)
        return str(image_id)
