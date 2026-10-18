import os
from celery import Celery

celery_app = Celery(
    "img_processing",
    broker=os.environ["CELERY_BROKER_URL"],
    backend=os.environ["CELERY_RESULT_BACKEND"],
    include=["src.celery_tasks"],   # modules that contain your @celery_app.task functions
)