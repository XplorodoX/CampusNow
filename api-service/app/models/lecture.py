from datetime import datetime

from pydantic import BaseModel, Field


class Lecture(BaseModel):
    lecture_id: str
    # Felder wie vom Frontend erwartet (timetable.json)
    title: str | None = Field(None, description="Alias für module_name – Frontend-kompatibel")
    module_name: str
    courseOfStudyId: str | None = Field(None, description="Alias für studiengang_id – Frontend-kompatibel")
    studiengang_id: str | None = None
    semesterId: str | None = Field(None, description="Semester-ID (z. B. 'sem_3')")
    semester: str | None = None
    room: str | None = Field(None, description="Raumnummer als String – Frontend-kompatibel")
    room_id: str | None = None
    building: str | None = None
    professor: str | None = None
    start_time: datetime | None = None
    startTime: str | None = Field(None, description="ISO-8601 Startzeit – Frontend-kompatibel")
    end_time: datetime | None = None
    endTime: str | None = Field(None, description="ISO-8601 Endzeit – Frontend-kompatibel")
    day_of_week: str | None = None
    duration_minutes: int = 90
    color: str | None = Field(None, description="Farbe für die Kalenderansicht (Hex, z. B. '#4A90D9')")
    recurrence: str | None = Field(None, description="Wiederholungsmuster: 'weekly', 'biweekly', 'once'")
    notes: str | None = Field(None, description="Notizen / Hinweise zur Vorlesung")

    class Config:
        from_attributes = True


class LectureResponse(Lecture):
    id: str | None = Field(None, alias="_id")

    class Config:
        from_attributes = True
        populate_by_name = True
