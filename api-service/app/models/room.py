from datetime import datetime

from pydantic import BaseModel, Field


class Room(BaseModel):
    room_number: str
    floor: int
    capacity: int
    building: str
    has_video: bool = False
    has_projector: bool = False
    street_view_enabled: bool = False

    class Config:
        from_attributes = True


class RoomImageInfo(BaseModel):
    image_paths: list[str] = []
    latest_update: datetime | None = None
    url_prefix: str


class RoomResponse(Room):
    id: str | None = Field(alias="_id")
    room_image_360: RoomImageInfo | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
