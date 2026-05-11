from pydantic import BaseModel, ConfigDict, Field


class CourseOfStudy(BaseModel):
    id: str
    label: str
    color: str


class Semester(BaseModel):
    id: str
    label: str


class EventGroup(BaseModel):
    id: str
    label: str
    color: str


class AppConfig(BaseModel):
    """Einmalig beim App-Start abgerufene Konfiguration: User-Settings + statische Metadaten."""

    model_config = ConfigDict(extra="ignore")

    # ── User-Einstellungen ──────────────────────────────────────────────
    notificationLeadMinutes: int = Field(15)
    defaultCourseOfStudyIds: list[str] = Field(default_factory=list)
    defaultSemesterIds: list[str] = Field(default_factory=list)
    defaultEventGroupIds: list[str] = Field(default_factory=list)
    savedLectureIds: list[str] = Field(default_factory=list)
    savedEventIds: list[str] = Field(default_factory=list)
    theme: str = Field("system")

    # ── Statische Metadaten (beim App-Start einmalig laden) ─────────────
    courses_of_study: list[CourseOfStudy] = Field(default_factory=list)
    semesters: list[Semester] = Field(default_factory=list)
    event_groups: list[EventGroup] = Field(default_factory=list)


class UserSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    notificationLeadMinutes: int = Field(
        15,
        description="Wie viele Minuten vor einer Vorlesung eine Benachrichtigung erscheinen soll",
    )
    defaultCourseOfStudyIds: list[str] = Field(
        default_factory=list,
        description="Vorausgewählte Studiengang-IDs",
    )
    defaultSemesterIds: list[str] = Field(
        default_factory=list,
        description="Vorausgewählte Semester-IDs",
    )
    defaultEventGroupIds: list[str] = Field(
        default_factory=list,
        description="Vorausgewählte Event-Gruppen-IDs",
    )
    savedLectureIds: list[str] = Field(
        default_factory=list,
        description="Vom Nutzer gespeicherte Vorlesungs-IDs",
    )
    savedEventIds: list[str] = Field(
        default_factory=list,
        description="Vom Nutzer gespeicherte Event-IDs",
    )
    theme: str = Field(
        "system",
        description="UI-Theme: `light`, `dark` oder `system`",
    )


class UserSettingsPatch(BaseModel):
    """Partielles Update – nur gesetzte Felder werden übernommen."""

    model_config = ConfigDict(extra="ignore")

    notificationLeadMinutes: int | None = Field(None, description="Minuten vor Benachrichtigung")
    defaultCourseOfStudyIds: list[str] | None = Field(None, description="Studiengang-IDs")
    defaultSemesterIds: list[str] | None = Field(None, description="Semester-IDs")
    defaultEventGroupIds: list[str] | None = Field(None, description="Event-Gruppen-IDs")
    savedLectureIds: list[str] | None = Field(None, description="Gespeicherte Vorlesungs-IDs")
    savedEventIds: list[str] | None = Field(None, description="Gespeicherte Event-IDs")
    theme: str | None = Field(None, description="UI-Theme: `light`, `dark` oder `system`")
