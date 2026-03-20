from datetime import datetime

from pydantic import BaseModel, Field


class ImageMetadata(BaseModel):
    room_id: str
    image_filename: str
    file_size_mb: float
    image_type: str = "360_panoramic"

    class Config:
        from_attributes = True


class ImageResponse(ImageMetadata):
    id: str | None = Field(alias="_id")
    image_path: str
    uploaded_at: datetime
    image_url_api: str

    class Config:
        from_attributes = True


class ImageListResponse(BaseModel):
    room_id: str
    images: list[ImageResponse] = []
    total_count: int = 0
