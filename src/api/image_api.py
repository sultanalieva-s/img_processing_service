import uuid
from typing import Annotated

from fastapi import APIRouter, UploadFile, Depends, HTTPException
from starlette import status
from starlette.responses import FileResponse

from src.db.models.image_models import Image
from src.dependencies.image_dependencies import get_sync_image_service, get_image_service
from src.schemas.image_schemas import UploadImageResponse, GetImageResponse, Page
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
