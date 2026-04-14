from datetime import datetime

from pydantic import BaseModel, Field


class Studiengang(BaseModel):
    name: str
    code: str
    semester: str = ""
    program_code: str | None = None
    program_name: str | None = None
    lecture_count: int = 0

    class Config:
        from_attributes = True


class StuDiengangResponse(Studiengang):
    id: str | None = Field(alias="_id")
    last_scraped: datetime | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
