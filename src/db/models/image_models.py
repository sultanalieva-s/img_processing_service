import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )


class ImageStatus(str, enum.Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


def _enum_column(enum_cls: type[enum.Enum]) -> Enum:
    # Stored as VARCHAR (not a native Postgres ENUM), which keeps Alembic
    # migrations simple when you add new statuses later.
    return Enum(
        enum_cls,
        native_enum=False,
        length=20,
        values_callable=lambda e: [member.value for member in e],
    )


class Image(TimestampMixin, Base):
    """An uploaded original image."""

    __tablename__ = "images"

    # UUID is generated in Python, so it exists BEFORE the insert and can be
    # used to build the storage key. It also can't be guessed or enumerated.
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    original_filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    width: Mapped[int]
    height: Mapped[int]

    # Key relative to the storage root, e.g. "images/<uuid>/original.jpg".
    # NOT an absolute path, so switching to S3 later needs no data migration.
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)

    status: Mapped[ImageStatus] = mapped_column(
        _enum_column(ImageStatus),
        default=ImageStatus.UPLOADED,
        index=True,
    )

    thumbnails: Mapped[list["ImageThumbnail"]] = relationship(
        back_populates="image",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ImageThumbnail(TimestampMixin, Base):
    """A generated thumbnail of an image."""

    __tablename__ = "image_thumbnails"
    __table_args__ = (
        # One row per (image, thumbnail name). A retried task overwrites the
        # file and upserts this row instead of creating duplicates.
        UniqueConstraint("image_id", "name", name="uq_image_thumbnail_name"),
        Index("ix_image_thumbnails_image_id", "image_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("images.id", ondelete="CASCADE"),
    )

    name: Mapped[str] = mapped_column(String(50))  # "thumb_128", "thumb_256", "thumb_512"
    format: Mapped[str] = mapped_column(String(10))  # "webp", "png", "jpeg"
    width: Mapped[int]
    height: Mapped[int]
    size_bytes: Mapped[int] = mapped_column(BigInteger)

    # e.g. "images/<uuid>/thumb_256.webp"
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)

    image: Mapped[Image] = relationship(back_populates="thumbnails")