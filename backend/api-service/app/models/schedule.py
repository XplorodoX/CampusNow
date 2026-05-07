from pydantic import BaseModel, Field, HttpUrl


class ScheduleSyncRequest(BaseModel):
    ical_url: str = Field(
        ...,
        description=(
            "Persönliche StarPlan-iCal-URL des Studierenden. "
            "Zu finden im HS-Aalen-Portal unter: Stundenplan → iCal-Export."
        ),
        examples=["https://vorlesungen.htw-aalen.de/splan/ical?type=pg&pgid=1234&lan=de"],
    )


class ScheduleEntry(BaseModel):
    uid: str | None = None
    module_name: str
    summary: str
    professor: str | None = None
    room_number: str | None = None
    room_id: str | None = None
    building_id: str | None = None
    room_known: bool = Field(
        False,
        description="True wenn der Raum in der CampusNow-Datenbank gefunden wurde",
    )
    start_time: str | None = None
    end_time: str | None = None
    day_of_week: str | None = None
    duration_minutes: int = 90
    imported_at: str | None = None


class ScheduleSyncResponse(BaseModel):
    total: int = Field(..., description="Gesamtanzahl der importierten Einträge")
    matched_rooms: int = Field(
        ...,
        description="Anzahl der Einträge, deren Raum in der DB gefunden wurde",
    )
    unmatched_rooms: list[str] = Field(
        default_factory=list,
        description="Raumnummern aus dem iCal, die in der DB nicht bekannt sind",
    )
    entries: list[ScheduleEntry] = Field(..., description="Alle geparsten Vorlesungen")
