import uuid

from sqlalchemy.exc import OperationalError

from src.celery_app import celery_app

from contextlib import contextmanager

from src.db.database import SyncSessionFactory
from src.db.repositories.sync.ImageRepositorySync import ImageRepositorySync
from src.storage.local_storage import get_storage
from src.utils.thumbnails import create_thumbnails

TRANSIENT_ERRORS = (OperationalError, ConnectionError, TimeoutError)


@contextmanager
def task_deps():
    with SyncSessionFactory() as session:
        yield ImageRepositorySync(session), get_storage()


@celery_app.task(
    autoretry_for=(OperationalError, ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=5,
)
def process_image(img_id: uuid.UUID):
    with task_deps() as (repo, storage):
        create_thumbnails(img_id, repo, storage)
