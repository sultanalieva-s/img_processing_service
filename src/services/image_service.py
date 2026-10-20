import uuid

from fastapi import UploadFile

from src.utils.image_validations import validate_image
from src.storage.local_storage import LocalStorage


def _clean_filename(name: str | None) -> str:
    """Keep the client's filename for display only: no folders, bounded length."""
    name = (name or "").replace("\x00", "").replace("\\", "/").split("/")[-1].strip()
    return name[:255] or "unnamed"



class ImageService:
    """asynchronous image service. (uses async repository) """

    def __init__(self, repo):
        self._repo = repo

    async def get(self, image_id: str):
        return await self._repo.get(image_id)

    async def get_all(self):
        return await self._repo.get_all()


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

        # 4. todo: enqueue a celery task:
        return str(image_id)
