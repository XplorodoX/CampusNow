from datetime import datetime

from pydantic import BaseModel, Field


class Lecture(BaseModel):
    lecture_id: str
    room_id: str
    studiengang_id: str
    professor: str | None = None
    module_name: str
    start_time: datetime
    end_time: datetime
    day_of_week: str
    duration_minutes: int
    semester: str | None = None

    class Config:
        from_attributes = True


class LectureResponse(Lecture):
    id: str | None = Field(alias="_id")

    class Config:
        from_attributes = True
