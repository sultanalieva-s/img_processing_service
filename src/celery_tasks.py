from src.celery_app import celery_app


@celery_app.task
def ping() -> str:
    return "pong"

@celery_app.task
def process_image(img_id: str):
    pass