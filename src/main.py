from fastapi import FastAPI

from src.api.image_api import router as img_router

app = FastAPI(
    title="image processing service",
    version="0.1.0",
    description="effective image processing service",
)

app.include_router(router=img_router, prefix="/images")