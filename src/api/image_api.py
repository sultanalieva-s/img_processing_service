from typing import Annotated

from fastapi import APIRouter, UploadFile, Depends
from starlette import status

from src.dependencies.image_dependencies import get_sync_image_service
from src.schemas.image_schemas import UploadImageResponse
from src.services.image_service import ImageServiceSync

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