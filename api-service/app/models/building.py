from datetime import datetime

from pydantic import BaseModel, Field


class Building(BaseModel):
    code: str = Field(..., description="Kürzel des Gebäudes (z. B. 'G2', 'H', 'Z')")
    name: str = Field(..., description="Vollständiger Name (z. B. 'Gebäude G2')")
    campus: str = Field(
        "Main",
        description="Campus-Standort: 'Main' (Hauptcampus) oder 'Burren'",
    )
    address: str | None = Field(None, description="Straßenadresse des Gebäudes")
    floors: list[int] = Field(
        default_factory=list,
        description="Liste der vorhandenen Stockwerke (z. B. [0, 1, 2])",
    )
    street_view_enabled: bool = Field(
        False,
        description="Ob 360°-Aufnahmen für dieses Gebäude verfügbar sind",
    )

    class Config:
        from_attributes = True


class BuildingResponse(Building):
    id: str | None = Field(None, alias="_id")
    room_count: int = Field(0, description="Anzahl der Räume in diesem Gebäude")
    last_scraped: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
        populate_by_name = True
