import uuid
from datetime import datetime
from typing import TypeVar, Generic

from pydantic import BaseModel, ConfigDict, Field, computed_field

T = TypeVar("T")


class UploadImageResponse(BaseModel):
    image_id: str

class GetImageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    image_id: uuid.UUID = Field(validation_alias="id")
    original_filename: str
    content_type: str
    size_bytes: int
    width: int
    height: int
    created_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        return f"/images/{self.image_id}/original"

class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int