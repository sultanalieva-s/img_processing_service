import uuid

from sqlalchemy.exc import OperationalError

from src.celery_app import celery_app

from contextlib import contextmanager

from src.db.database import SyncSessionFactory
from src.db.repositories.sync.ImageRepositorySync import ImageRepositorySync
from src.storage.local_storage import get_storage
from src.utils.thumbnails import create_thumbnails

TRANSIENT_ERRORS = (OperationalError, ConnectionError, TimeoutError)


def retrying_task(
        *,
        max_retries: int = 5,
        retry_for: tuple[type[Exception], ...] = TRANSIENT_ERRORS,
        **options,
):
    """Celery task decorator with sensible retry defaults.

    Wait time between attempts grows exponentially (1s, 2s, 4s, 8s, ...), is capped
    at 5 minutes, and gets random jitter so many failing tasks don't retry at once.
    After `max_retries` failed retries the task fails and shows up in Flower.
    """
    return celery_app.task(
        autoretry_for=retry_for,
        retry_backoff=True,
        retry_backoff_max=300,
        retry_jitter=True,
        max_retries=max_retries,
        acks_late=True,  # a task is re-delivered if the worker dies while running it
        **options,
    )


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
