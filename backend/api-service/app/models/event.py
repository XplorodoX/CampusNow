from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., description="Titel des Events")
    groupId: str | None = Field(None, description="Event-Gruppe (z. B. 'career', 'sports')")
    start_time: datetime | None = Field(None, description="Startzeit")
    end_time: datetime | None = Field(None, description="Endzeit")
    building: str | None = Field(None, description="Gebäude-Code (z. B. 'G2')")
    room: str | None = Field(None, description="Raumnummer")
    organizer: str | None = Field(None, description="Veranstalter")
    is_public: bool = Field(True, description="Sichtbar für Gäste ohne Login")
    image_url: str | None = Field(None, description="Vorschaubild-URL")
    detail_url: str | None = Field(None, description="Link zur Original-Seite")
    description: str | None = Field(None, description="Beschreibung")
    registration_url: str | None = Field(None, description="Anmeldelink")
    registration_deadline: str | None = Field(None, description="Anmeldefrist")


class EventResponse(EventCreate):
    id: str | None = Field(None, alias="_id")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )
