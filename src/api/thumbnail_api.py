import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel

from src.db.models.image_models import ImageThumbnail
from src.dependencies.image_dependencies import get_image_service
from src.schemas.image_schemas import Page
from src.services.image_service import ImageService
from src.utils.thumbnails import THUMBNAIL_SIZES

THUMBNAIL_FILE_ROUTE = "get_thumbnail_file"

router = APIRouter(prefix="/thumbnails", tags=["thumbnails"])


class ThumbnailItem(BaseModel):
    image_id: uuid.UUID
    name: str  # "thumb_256"
    format: str  # "webp"
    width: int
    height: int
    size_bytes: int
    url: str  # where to download the file


def _file_url(request: Request, thumb: ImageThumbnail) -> str:
    return str(
        request.url_for(THUMBNAIL_FILE_ROUTE, image_id=thumb.image_id, name=thumb.name)
    )


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=Page[ThumbnailItem],
)
async def get_thumbnails(
    request: Request,
    service: Annotated[ImageService, Depends(get_image_service)],
    size: Annotated[int, Query(description="Exact thumbnail size: 128, 256 or 512")] = 256,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """For feed: thumbnails of ONE size across all images, newest images first.

    Only images that already have this thumbnail are included. The client
    renders `<img src=url>` and the browser downloads each file itself.
    """
    if size not in THUMBNAIL_SIZES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"size must be one of {sorted(THUMBNAIL_SIZES)}",
        )

    thumbs, total = await service.get_thumbnails_by_size(
        size=size, limit=limit, offset=offset
    )

    items = [
        ThumbnailItem(
            image_id=t.image_id,
            name=t.name,
            format=t.format,
            width=t.width,
            height=t.height,
            size_bytes=t.size_bytes,
            url=_file_url(request, t),
        )
        for t in thumbs
    ]
    return Page[ThumbnailItem](items=items, total=total, limit=limit, offset=offset)