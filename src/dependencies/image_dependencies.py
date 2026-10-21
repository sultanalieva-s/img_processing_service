from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.db.repositories.asynch.image_repository import ImageRepository
from src.db.repositories.sync.ImageRepositorySync import ImageRepositorySync
from src.dependencies.database_dependencies import get_session, get_sync_session
from src.services.image_service import ImageService, ImageServiceSync
from src.storage.local_storage import LocalStorage


def get_sync_image_repository(session: Session = Depends(get_sync_session)):
    return ImageRepositorySync(session)

def get_sync_image_service(
    repo: Annotated[ImageRepositorySync, Depends(get_sync_image_repository)]
) -> ImageServiceSync:
    st = LocalStorage("/data/uploads")
    return ImageServiceSync(repo, st)

def get_image_repository(session: AsyncSession = Depends(get_session)):
    return ImageRepository(session)

def get_image_service(
    repo: Annotated[ImageRepository, Depends(get_image_repository)]
) -> ImageService:
    st = LocalStorage("/data/uploads")
    return ImageService(repo, st)