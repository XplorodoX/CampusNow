from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class EventCategory(str, Enum):
    VORTRAG = "Vortrag"
    SPORT = "Sport"
    KULTUR = "Kultur"
    MENSA = "Mensa"
    HOCHSCHULE = "Hochschule"
    SONSTIGES = "Sonstiges"


class EventCreate(BaseModel):
    title: str = Field(..., description="Titel des Events")
    description: str | None = Field(None, description="Beschreibung / Details zum Event")
    # groupId ist der Frontend-kompatible Name, category der interne
    groupId: str | None = Field(
        None,
        description="Event-Gruppen-ID (timetable.json kompatibel, z. B. 'sports', 'career')",
    )
    category: EventCategory = Field(
        EventCategory.SONSTIGES,
        description="Kategorie des Events",
    )
    start_time: datetime | None = Field(None, description="Startzeit (intern)")
    startTime: str | None = Field(None, description="ISO-8601 Startzeit – Frontend-kompatibel")
    end_time: datetime | None = Field(None, description="Endzeit (intern)")
    endTime: str | None = Field(None, description="ISO-8601 Endzeit – Frontend-kompatibel")
    building_id: str | None = Field(None, description="Gebäude-ID (z. B. 'G2')")
    building: str | None = Field(None, description="Gebäudename als String – Frontend-kompatibel")
    room_id: str | None = Field(None, description="Raum-ID aus der Rooms-Collection")
    location: str | None = Field(None, description="Ortsangabe als Freitext (Frontend-kompatibel)")
    location_text: str | None = Field(None, description="Alias für location – intern")
    organizer: str | None = Field(None, description="Veranstalter (Person oder Organisation)")
    is_public: bool = Field(True, description="Sichtbar für Gäste ohne Login")
    color: str | None = Field(None, description="Farbe für die Kalenderansicht (Hex, z. B. '#F39C12')")
    imageUrl: str | None = Field(None, description="Vorschaubild-URL – Frontend-kompatibel (camelCase)")
    image_url: str | None = Field(None, description="Vorschaubild-URL – intern (snake_case)")

    class Config:
        from_attributes = True


class EventResponse(EventCreate):
    id: str | None = Field(None, alias="_id")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
        populate_by_name = True
