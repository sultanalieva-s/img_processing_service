from pydantic import BaseModel

class UploadImageRequest(BaseModel):
    pass

class UploadImageResponse(BaseModel):
    image_id: str


class GetImageResponse(BaseModel):
    image_id: str
    image_url: str
