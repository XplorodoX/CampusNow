"""Timetable router – kombinierter Endpunkt wie timetable.json für das Frontend."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.utils import serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/timetable", tags=["timetable"])

# Feste Semester-Liste (entspricht timetable.json)
_SEMESTERS = [
    {"id": f"sem_{i}", "label": f"Semester {i}"} for i in range(1, 8)
]

# Event-Gruppen (entspricht timetable.json event_groups)
_EVENT_GROUPS = [
    {"id": "sports",  "label": "Sports & Fitness"},
    {"id": "culture", "label": "Culture & Arts"},
    {"id": "career",  "label": "Career & Networking"},
    {"id": "social",  "label": "Social Events"},
]


def _lecture_to_frontend(lec: dict) -> dict:
    """Mappt ein DB-Lecture-Dokument auf das timetable.json-Format."""
    def _to_iso(value: Any) -> str | None:
        if value is None:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    start = lec.get("startTime") or (
        _to_iso(lec.get("start_time"))
    )
    end = lec.get("endTime") or (
        _to_iso(lec.get("end_time"))
    )
    return {
        "id": str(lec.get("_id") or lec.get("lecture_id", "")),
        "title": lec.get("title") or lec.get("module_name", ""),
        "courseOfStudyId": lec.get("courseOfStudyId") or lec.get("studiengang_id"),
        "semesterId": lec.get("semesterId") or lec.get("semester"),
        "room": lec.get("room") or lec.get("room_number"),
        "building": lec.get("building") or lec.get("building_id"),
        "professor": lec.get("professor"),
        "startTime": start,
        "endTime": end,
        "color": lec.get("color", "#4A90D9"),
        "recurrence": lec.get("recurrence", "weekly"),
        "notes": lec.get("notes", ""),
    }


def _event_to_frontend(evt: dict) -> dict:
    """Mappt ein DB-Event-Dokument auf das timetable.json-Format."""
    def _to_iso(value: Any) -> str | None:
        if value is None:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    start = evt.get("startTime") or (
        _to_iso(evt.get("start_time"))
    )
    end = evt.get("endTime") or (
        _to_iso(evt.get("end_time"))
    )
    return {
        "id": str(evt.get("_id", "")),
        "title": evt.get("title", ""),
        "groupId": evt.get("groupId") or evt.get("category", "Sonstiges"),
        "location": evt.get("location") or evt.get("location_text", ""),
        "building": evt.get("building") or evt.get("building_id", ""),
        "organizer": evt.get("organizer"),
        "startTime": start,
        "endTime": end,
        "color": evt.get("color", "#F39C12"),
        "description": evt.get("description", ""),
        "imageUrl": evt.get("imageUrl") or evt.get("image_url"),
    }


@router.get(
    "",
    summary="Stundenplan abrufen – timetable.json-Format",
    response_description="Kombinierte Struktur mit courses_of_study, semesters, event_groups, lectures und events",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "courses_of_study": [{"id": "cs_b3", "label": "Computer Science"}],
                        "semesters": [{"id": "sem_3", "label": "Semester 3"}],
                        "event_groups": [{"id": "sports", "label": "Sports & Fitness"}],
                        "lectures": [{"id": "lec_001", "title": "Algorithms & Data Structures"}],
                        "events": [{"id": "evt_001", "title": "Campus Run 5K"}],
                    }
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_timetable(
    courseOfStudyId: str | None = Query(
        None, description="Filtert Vorlesungen nach Studiengangs-ID"
    ),
    semesterId: str | None = Query(
        None, description="Filtert Vorlesungen nach Semester-ID"
    ),
    limit_lectures: int = Query(200, ge=1, le=1000, description="Max. Vorlesungen"),
    limit_events: int = Query(50, ge=1, le=200, description="Max. Events"),
) -> dict[str, Any]:
    """Gibt alle Daten zurück, die das Frontend für die Timetable-Ansicht benötigt.

    Entspricht exakt der Struktur von `timetable.json`:
    - `courses_of_study` – alle Studiengänge
    - `semesters` – feste Semester-Liste (1–7)
    - `event_groups` – feste Gruppen-Liste
    - `lectures` – Vorlesungen (optional gefiltert)
    - `events` – Campus-Events
    """
    try:
        db = mongo_client.get_db()

        # Studiengänge → courses_of_study
        studiengaenge = list(db.studiengaenge.find({}, {"_id": 1, "name": 1, "code": 1}))
        courses_of_study = [
            {"id": str(s.get("_id") or s.get("code", "")), "label": s.get("name", "")}
            for s in studiengaenge
        ]

        # Vorlesungen mit optionalen Filtern
        lec_query: dict[str, Any] = {}
        if courseOfStudyId:
            lec_query["$or"] = [
                {"courseOfStudyId": courseOfStudyId},
                {"studiengang_id": courseOfStudyId},
            ]
        if semesterId:
            lec_query["$or"] = lec_query.get("$or", []) + [
                {"semesterId": semesterId},
                {"semester": semesterId},
            ]

        raw_lectures = serialize_docs(list(db.lectures.find(lec_query).limit(limit_lectures)))
        lectures = [_lecture_to_frontend(l) for l in raw_lectures]

        # Events
        raw_events = serialize_docs(list(db.events.find({}).limit(limit_events)))
        events = [_event_to_frontend(e) for e in raw_events]

        return {
            "courses_of_study": courses_of_study,
            "semesters": _SEMESTERS,
            "event_groups": _EVENT_GROUPS,
            "lectures": lectures,
            "events": events,
        }

    except Exception as e:
        logger.error(f"Error fetching timetable: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
