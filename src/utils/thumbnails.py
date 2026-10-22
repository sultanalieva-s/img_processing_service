import io
import logging
import uuid

from PIL import Image as PILImage
from PIL import ImageOps, UnidentifiedImageError

from src.db.models.image_models import Image
from src.db.repositories.sync import ImageRepositorySync
from src.storage.local_storage import LocalStorage

logger = logging.getLogger(__name__)

THUMBNAIL_SIZES = (128, 256, 512)  # longest side, in pixels
OUTPUT_FORMAT = "WEBP"
OUTPUT_EXTENSION = "webp"
OUTPUT_QUALITY = 80


def render_thumbnail(source: PILImage.Image, size: int) -> tuple[bytes, int, int]:
    """Shrink `source` so its longest side is at most `size`.

    Pure function: no database, no storage. Returns (encoded bytes, width, height).
    """
    thumb = source.copy()  # thumbnail() works in place, so never touch the source
    thumb.thumbnail((size, size), PILImage.Resampling.LANCZOS)  # keeps ratio, never upscales

    # WebP stores RGB or RGBA, so convert other modes (P, L, LA, CMYK, ...)
    if thumb.mode not in ("RGB", "RGBA"):
        has_alpha = "A" in thumb.mode or "transparency" in thumb.info
        thumb = thumb.convert("RGBA" if has_alpha else "RGB")

    buffer = io.BytesIO()
    # EXIF and other metadata are not copied, which also strips GPS data
    thumb.save(buffer, format=OUTPUT_FORMAT, quality=OUTPUT_QUALITY)
    return buffer.getvalue(), thumb.width, thumb.height


def create_thumbnails(
    image_id: uuid.UUID,
    repo: ImageRepositorySync,
    storage: LocalStorage,
) -> None:
    img: Image | None = repo.get(image_id)
    if img is None:
        # deleted before the task ran: retrying can never succeed
        logger.warning("create_thumbnails: image %s not found, skipping", image_id)
        return

    # read what we need up front
    original_id = img.id
    original_path = storage.path(img.storage_key)

    if not original_path.is_file():
        logger.error("create_thumbnails: original file missing for image %s", image_id)
        return

    try:
        with PILImage.open(original_path) as opened:
            # apply EXIF rotation, otherwise phone photos come out sideways
            source = ImageOps.exif_transpose(opened)

            for size in THUMBNAIL_SIZES:
                data, width, height = render_thumbnail(source, size)

                name = f"thumb_{size}"
                # deterministic key: a retried task overwrites the same file
                key = f"images/{original_id}/{name}.{OUTPUT_EXTENSION}"

                # file first, then the row, so a row never points at a missing file
                storage.save(key, io.BytesIO(data))
                repo.upsert_thumbnail(
                    image_id=original_id,
                    name=name,
                    format=OUTPUT_EXTENSION,
                    width=width,
                    height=height,
                    size_bytes=len(data),
                    storage_key=key,
                )
    except (UnidentifiedImageError, PILImage.DecompressionBombError):
        # permanent: the file can't be decoded, so retrying won't help
        logger.exception("create_thumbnails: cannot decode image %s", image_id)
        return

    logger.info("create_thumbnails: created %d thumbnails for image %s", len(THUMBNAIL_SIZES), image_id)