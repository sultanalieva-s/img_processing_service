import os
from dataclasses import dataclass
from typing import BinaryIO

from PIL import Image as PILImage
from PIL import UnidentifiedImageError

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_PIXELS = 50_000_000  # guards against decompression bombs

# Pillow format name -> (content type, file extension)
ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    "JPEG": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class ImageValidationError(Exception):
    """Base class: the upload is not acceptable."""


class FileTooLargeError(ImageValidationError):
    pass


class UnsupportedImageTypeError(ImageValidationError):
    pass


class InvalidImageError(ImageValidationError):
    pass


@dataclass(frozen=True)
class ImageMeta:
    format: str
    content_type: str
    extension: str
    width: int
    height: int
    size_bytes: int


def _size_of(f: BinaryIO) -> int:
    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    return size


def validate_image(f: BinaryIO) -> ImageMeta:
    """Validate an uploaded file and return trusted metadata.

    Everything returned here is detected from the file's bytes, never taken
    from the client-provided filename or content type. The stream is rewound
    to the start before returning, so it can be saved right after.
    """
    size = _size_of(f)
    if size == 0:
        raise InvalidImageError("The file is empty.")
    if size > MAX_UPLOAD_BYTES:
        raise FileTooLargeError(
            f"The file is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB."
        )

    try:
        with PILImage.open(f) as img:  # reads the header only, does not decode
            fmt = img.format
            width, height = img.size

            if fmt not in ALLOWED_FORMATS:
                raise UnsupportedImageTypeError("Only JPEG, PNG and WebP are allowed.")
            if width * height > MAX_PIXELS:
                raise InvalidImageError("The image dimensions are too large.")

            img.verify()  # checks file integrity without a full decode
    except ImageValidationError:
        raise
    except (
        UnidentifiedImageError,
        PILImage.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ) as exc:
        raise InvalidImageError("The file is not a valid image.") from exc
    finally:
        f.seek(0)

    content_type, extension = ALLOWED_FORMATS[fmt]
    return ImageMeta(
        format=fmt,
        content_type=content_type,
        extension=extension,
        width=width,
        height=height,
        size_bytes=size,
    )