from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class Room(BaseModel):
    room_number: str
    floor: int | None = Field(None, description="Stockwerk (wird vom Scraper aus dem Raumnamen extrahiert)")
    capacity: int | None = Field(None, description="Kapazität – manuell pflegbar")
    building: str | None = Field(None, description="Gebäude-Kürzel (z. B. 'G2', 'H')")
    building_id: str | None = Field(None, description="Referenz auf das Building-Dokument")
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
