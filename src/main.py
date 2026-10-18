from fastapi import FastAPI

app = FastAPI(
    title="image processing service",
    version="0.1.0",
    description="service that effectively handles images",
)