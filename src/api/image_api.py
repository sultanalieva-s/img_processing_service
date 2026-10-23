import uuid
from typing import Annotated

from fastapi import APIRouter, UploadFile, Depends, HTTPException, Path
from starlette import status
from starlette.requests import Request
from starlette.responses import FileResponse

from src.db.models.image_models import Image, ImageThumbnail
from src.dependencies.image_dependencies import get_sync_image_service, get_image_service
from src.schemas.image_schemas import UploadImageResponse, GetImageResponse, Page, ThumbnailResponse
from src.services.image_service import ImageServiceSync, ImageService

router = APIRouter()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UploadImageResponse,
)
def upload_image(
        file: UploadFile,
        service: Annotated[ImageServiceSync, Depends(get_sync_image_service)]
):
    img_id = service.upload(file)
    return {"image_id": img_id}

@router.get(
    "/{image_id}",
    status_code=status.HTTP_200_OK,
    response_model=GetImageResponse,
)
async def get_image(
        image_id: uuid.UUID,
        service: Annotated[ImageService, Depends(get_image_service)]
):
    img: Image = await service.get(image_id)
    if img is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return GetImageResponse.model_validate(img)

@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=Page[GetImageResponse],
)
async def get_images(
        service: Annotated[ImageService, Depends(get_image_service)],
        limit: int = 10,
        offset: int = 0,
):
    images, total = await service.get_all(lim=limit, off=offset)
    return Page[GetImageResponse](
        items=[GetImageResponse.model_validate(i) for i in images],
        total=total,
        limit=limit,
        offset=offset,
    )

FILE_HEADERS = {
    "Cache-Control": "public, max-age=86400",
    "X-Content-Type-Options": "nosniff",
}

@router.get("/{image_id}/original")
async def get_original(
    image_id: uuid.UUID,
    service: Annotated[ImageService, Depends(get_image_service)],
):
    img_file = await service.get_img_file(image_id)
    if img_file is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")
    return FileResponse(
        img_file.path,
        media_type=img_file.media_type,
        filename=img_file.filename,
        content_disposition_type="inline",   # show in the browser, don't force a download
        headers=FILE_HEADERS,
    )

# thumbnails
# GET /images/{image_id}/thumbnails/{thumbnail_name}: get image's thumbnail file by name
@router.get(
    "/{image_id}/thumbnails/{name}",
    status_code=status.HTTP_200_OK,
    response_class=FileResponse,
    responses={
        200: {"content": {"image/webp": {}}, "description": "The thumbnail file"},
        404: {"description": "Image or thumbnail not found"},
    },
)
async def get_thumbnail_file(
        image_id: uuid.UUID,
        name: Annotated[str, Path(max_length=50, description="e.g. thumb_256")],
        service: Annotated[ImageService, Depends(get_image_service)],
):
    file = await service.get_thumbnail_file(image_id, name)
    if file is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thumbnail not found")

    return FileResponse(
        file.path,
        media_type=file.media_type,
        content_disposition_type="inline",  # display in the browser, don't force a download
        headers=FILE_HEADERS,
    )

THUMBNAIL_FILE_ROUTE = "get_thumbnail_file"

# GET /images/{image_id}/thumbnails : returns a list of thumbnails metadata for an image
def _thumbnail_url(request: Request, thumb: ImageThumbnail) -> str:
    return str(
        request.url_for(THUMBNAIL_FILE_ROUTE, image_id=thumb.image_id, name=thumb.name)
    )
@router.get(
    "/{image_id}/thumbnails",
    status_code=status.HTTP_200_OK,
    response_model=list[ThumbnailResponse],
)
async def get_thumbnails(
        image_id: uuid.UUID,
        request: Request,
        service: Annotated[ImageService, Depends(get_image_service)],
):
    """All thumbnails that exist for an image. An empty list means 'not ready yet'."""
    thumbs = await service.get_thumbnails(image_id)
    if thumbs is None:  # the image itself doesn't exist
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Image not found")

    return [
        ThumbnailResponse(
            name=t.name,
            format=t.format,
            width=t.width,
            height=t.height,
            size_bytes=t.size_bytes,
            url=_thumbnail_url(request, t),
        )
        for t in thumbs
    ]
