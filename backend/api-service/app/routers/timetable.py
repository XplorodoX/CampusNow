"""Timetable router – kombinierter Endpunkt wie timetable.json für das Frontend."""

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.utils import serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/timetable", tags=["timetable"])

_SEMESTERS = [
    {"id": f"sem_{i}", "label": f"Semester {i}"} for i in range(1, 8)
]

_EVENT_GROUPS = [
    {"id": "sports",  "label": "Sports & Fitness"},
    {"id": "culture", "label": "Culture & Arts"},
    {"id": "career",  "label": "Career & Networking"},
    {"id": "social",  "label": "Social Events"},
]

# Kategorie-Werte aus dem Scraper → frontend groupId
_CATEGORY_TO_GROUP: dict[str, str] = {
    "sport": "sports", "sports": "sports", "fitness": "sports",
    "kultur": "culture", "culture": "culture",
    "karriere": "career", "career": "career", "networking": "career",
    "vortrag": "career",
    "hochschule": "social", "social": "social", "sonstiges": "social",
    "mensa": "social",
}

_GROUP_COLORS: dict[str, str] = {
    "sports": "#F39C12",
    "culture": "#9B59B6",
    "career": "#2ECC71",
    "social": "#3498DB",
}


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _parse_date(date_str: str) -> datetime | None:
    """Parsed YYYY-MM-DD oder vollständigen ISO-String zu datetime."""
    if not date_str:
        return None
    try:
        return datetime.fromisoformat(date_str)
    except ValueError:
        pass
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def _lecture_to_frontend(lec: dict) -> dict:
    """Mappt ein DB-Lecture-Dokument auf das timetable.json-Format."""
    semester_ids: list = lec.get("semesterIds") or []
    return {
        "id":             str(lec.get("_id") or lec.get("lecture_id", "")),
        "title":          lec.get("module_name", ""),
        "moduleId":       lec.get("module_id"),
        "courseOfStudyId": lec.get("courseOfStudyId", ""),
        "semesterId":     semester_ids[0] if semester_ids else "",
        "semesterIds":    semester_ids,
        "room":           lec.get("room_number", ""),
        "building":       lec.get("building", ""),
        "professor":      lec.get("professor") or "",
        "startTime":      _to_iso(lec.get("start_time")),
        "endTime":        _to_iso(lec.get("end_time")),
        "dayOfWeek":      lec.get("day_of_week", ""),
        "durationMinutes": lec.get("duration_minutes", 90),
        "color":          lec.get("color", "#4A90D9"),
        "recurrence":     lec.get("recurrence", "weekly"),
    }


def _event_to_frontend(evt: dict) -> dict:
    """Mappt ein DB-Event-Dokument auf das timetable.json-Format."""
    group_id = _CATEGORY_TO_GROUP.get((evt.get("groupId") or "").lower(), "social")
    result: dict = {
        "id":        str(evt.get("_id", "")),
        "title":     evt.get("title", ""),
        "groupId":   group_id,
        "startTime": _to_iso(evt.get("start_time")),
        "endTime":   _to_iso(evt.get("end_time")),
        "color":     _GROUP_COLORS.get(group_id, "#3498DB"),
        "is_public": evt.get("is_public", True),
        "detail_url": evt.get("detail_url"),
    }
    # Optionale Felder nur wenn vorhanden (von Detailseite)
    for field in ("description", "organizer", "registration_url", "registration_deadline"):
        val = evt.get(field)
        if val:
            result[field] = val
    return result


@router.get(
    "",
    summary="Stundenplan abrufen – timetable.json-Format",
    response_description="Kombinierte Struktur mit courses_of_study, semesters, event_groups, lectures und events",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "courses_of_study": [{"id": "INF S1+2", "label": "Informatik Sem. 1+2"}],
                        "semesters": [{"id": "sem_3", "label": "Semester 3"}],
                        "event_groups": [{"id": "sports", "label": "Sports & Fitness"}],
                        "lectures": [{"id": "lec_001", "title": "Algorithmen & Datenstrukturen"}],
                        "events": [{"id": "evt_001", "title": "Campus Run 5K"}],
                    }
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_timetable(
    course: str | None = Query(
        None,
        description="Studiengangs-IDs, mehrere mit Komma (z. B. `INF S1+2,INF S3+4`)",
    ),
    semester: str | None = Query(
        None,
        description="Semester-IDs, mehrere mit Komma (z. B. `sem_3,sem_4`)",
    ),
    event_group: str | None = Query(
        None,
        description="Event-Gruppen-IDs, mehrere mit Komma (z. B. `sports,career`)",
    ),
    building: str | None = Query(
        None,
        description="Filtert Vorlesungen und Events nach Gebäude-Kürzel (exakter Match, z. B. `G2`)",
    ),
    room: str | None = Query(
        None,
        description="Filtert Vorlesungen nach Raum (Partial-Match, case-insensitiv, z. B. `G2 1`)",
    ),
    professor: str | None = Query(
        None,
        description="Filtert Vorlesungen nach Dozent (Partial-Match, case-insensitiv)",
    ),
    date_from: str | None = Query(
        None,
        description="Nur Einträge ab diesem Datum (YYYY-MM-DD)",
    ),
    date_to: str | None = Query(
        None,
        description="Nur Einträge bis zu diesem Datum (YYYY-MM-DD, inklusive)",
    ),
    recurrence: str | None = Query(
        None,
        description="Wiederholungstyp: `weekly` oder `once`",
    ),
    public_only: bool = Query(False, description="Nur öffentliche Events zurückgeben"),
    limit_lectures: int = Query(200, ge=1, le=1000, description="Max. Vorlesungen"),
    limit_events: int = Query(50, ge=1, le=200, description="Max. Events"),
) -> dict[str, Any]:
    """Gibt alle Daten zurück, die das Frontend für die Timetable-Ansicht benötigt.

    Entspricht exakt der Struktur von `timetable.json`.
    Alle Filter-Parameter sind optional und kombinierbar.
    """
    try:
        db = mongo_client.get_db()

        # courses_of_study aus DB – code-Feld als ID, damit Filter-Werte matchbar sind
        studiengaenge = list(db.studiengaenge.find({}, {"code": 1, "name": 1}))
        courses_of_study = [
            {
                "id": s.get("code") or str(s.get("_id", "")),
                "label": s.get("name", ""),
            }
            for s in studiengaenge
        ]

        # ── Lecture-Query aufbauen ──────────────────────────────────────
        lec_clauses: list[dict] = []

        if course:
            ids = [c.strip() for c in course.split(",")]
            lec_clauses.append({"$or": [
                {"courseOfStudyId": {"$in": ids}},
                {"course_code": {"$in": ids}},
            ]})
        if semester:
            sids = [s.strip() for s in semester.split(",")]
            lec_clauses.append({"$or": [
                {"semesterIds": {"$in": sids}},
                {"semesterId": {"$in": sids}},
            ]})
        if building:
            lec_clauses.append({"$or": [
                {"building": building},
                {"building_id": building},
            ]})
        if room:
            lec_clauses.append({"$or": [
                {"room": {"$regex": room, "$options": "i"}},
                {"room_number": {"$regex": room, "$options": "i"}},
            ]})
        if professor:
            lec_clauses.append({"professor": {"$regex": professor, "$options": "i"}})
        if date_from:
            dt = _parse_date(date_from)
            if dt:
                lec_clauses.append({"start_time": {"$gte": dt}})
        if date_to:
            dt = _parse_date(date_to)
            if dt:
                lec_clauses.append({"start_time": {"$lte": dt.replace(hour=23, minute=59, second=59)}})
        if recurrence:
            lec_clauses.append({"recurrence": recurrence})

        lec_query: dict[str, Any] = {"$and": lec_clauses} if lec_clauses else {}
        raw_lectures = serialize_docs(list(db.lectures.find(lec_query).limit(limit_lectures)))
        lectures = [_lecture_to_frontend(lec) for lec in raw_lectures]

        # ── Event-Query aufbauen ────────────────────────────────────────
        evt_clauses: list[dict] = []

        if public_only or course:
            evt_clauses.append({"is_public": True})
        if event_group:
            gids = [g.strip() for g in event_group.split(",")]
            evt_clauses.append({"$or": [
                {"groupId": {"$in": gids}},
                {"category": {"$in": [_CATEGORY_TO_GROUP.get(g.lower(), g) for g in gids]}},
            ]})
        if building:
            evt_clauses.append({"$or": [
                {"building": building},
                {"building_id": building},
            ]})
        if date_from:
            evt_clauses.append({"start_time": {"$gte": date_from}})
        if date_to:
            evt_clauses.append({"start_time": {"$lte": date_to + "T23:59:59"}})

        evt_query: dict[str, Any] = {"$and": evt_clauses} if evt_clauses else {}
        raw_events = serialize_docs(list(db.events.find(evt_query).limit(limit_events)))
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
