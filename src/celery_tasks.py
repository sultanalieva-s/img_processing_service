import uuid

from src.celery_app import celery_app

from contextlib import contextmanager

from src.db.database import SyncSessionFactory
from src.db.repositories.sync.ImageRepositorySync import ImageRepositorySync
from src.storage.local_storage import get_storage
from src.utils.thumbnails import create_thumbnails


@contextmanager
def task_deps():
    with SyncSessionFactory() as session:
        yield ImageRepositorySync(session), get_storage()

@celery_app.task
def process_image(img_id: uuid.UUID):
    with task_deps() as (repo, storage):
        create_thumbnails(img_id, repo, storage)
