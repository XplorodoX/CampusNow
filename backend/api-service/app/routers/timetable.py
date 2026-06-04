"""Timetable router – kombinierter Endpunkt wie timetable.json für das Frontend."""

import hashlib
import logging
from datetime import datetime
from typing import Any
from bson import ObjectId

from fastapi import APIRouter, Header, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.utils import serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/timetable", tags=["timetable"])

_SEMESTERS = [
    {"id": f"sem_{i}", "label": f"Semester {i}"} for i in range(1, 8)
]

_EVENT_GROUPS = [
    {"id": "sports",        "label": "Sports & Fitness",       "color": "#F39C12"},
    {"id": "workshops",     "label": "Workshops & Training",   "color": "#E74C3C"},
    {"id": "academic",      "label": "Academic Events",       "color": "#3498DB"},
    {"id": "culture",       "label": "Culture & Arts",        "color": "#9B59B6"},
    {"id": "alumni",        "label": "Alumni Events",         "color": "#2E8B57"},
    {"id": "international", "label": "International Events",  "color": "#16A085"},
    {"id": "career",        "label": "Career & Networking",   "color": "#2ECC71"},
    {"id": "social",        "label": "Social Events",         "color": "#95A5A6"},
]

# Kategorie-Werte aus dem Scraper → frontend groupId
_CATEGORY_TO_GROUP: dict[str, str] = {
    "sports": "sports", "fitness": "sports",
    "workshops": "workshops", "workshop": "workshops", "training": "workshops", "kurs": "workshops",
    "academic": "academic", "forschung": "academic", "research": "academic", "symposium": "academic",
    "kultur": "culture", "culture": "culture", "arts": "culture",
    "alumni": "alumni", "absolvent": "alumni",
    "international": "international", "erasmus": "international", "exchange": "international",
    "career": "career", "networking": "career", "karriere": "career",
    "social": "social", "hochschule": "social", "sonstiges": "social", "mensa": "social",
}

_GROUP_COLORS: dict[str, str] = {g["id"]: g["color"] for g in _EVENT_GROUPS}


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
        "room":           lec.get("room_number", ""),
        "building":       lec.get("building", ""),
        "professor":      lec.get("professor") or "",
        "startTime":      _to_iso(lec.get("start_time")),
        "endTime":        _to_iso(lec.get("end_time")),
        "dayOfWeek":      lec.get("day_of_week", ""),
        "durationMinutes": lec.get("duration_minutes", 90),
        "recurrence":     lec.get("recurrence", "weekly"),
    }


def _event_to_frontend(evt: dict, mock_rooms: list[dict] | None = None) -> dict:
    """Mappt ein DB-Event-Dokument auf das timetable.json-Format."""
    group_id = _CATEGORY_TO_GROUP.get((evt.get("groupId") or "").lower(), "social")
    event_id = str(evt.get("_id", ""))
    image_url = evt.get("image_url") or f"https://picsum.photos/seed/{event_id}/800/450"

    # building/room: echte Daten bevorzugen, sonst deterministisch aus Pool wählen
    building = evt.get("building") or ""
    room = evt.get("room") or ""
    if (not building or not room) and mock_rooms:
        idx = int(hashlib.md5(event_id.encode()).hexdigest(), 16) % len(mock_rooms)
        mock = mock_rooms[idx]
        building = building or mock.get("building_id") or ""
        room = room or mock.get("room_number") or ""

    result: dict = {
        "id":        event_id,
        "title":     evt.get("title", ""),
        "groupId":   group_id,
        "color":     _GROUP_COLORS.get(group_id, "#95A5A6"),
        "startTime": _to_iso(evt.get("start_time")),
        "endTime":   _to_iso(evt.get("end_time")),
        "is_public": evt.get("is_public", True),
        "detail_url": evt.get("detail_url"),
        "image_url":  image_url,
        "building":   building,
        "room":       room,
    }
    # Optionale Felder nur wenn vorhanden (von Detailseite)
    for field in ("description", "organizer", "registration_url", "registration_deadline"):
        val = evt.get(field)
        if val:
            result[field] = val
    return result


@router.get(
    "",
    summary="Stundenplan abrufen",
    response_description="Gefilterte Vorlesungen und Events",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "lectures": [{"id": "lec_001", "title": "Algorithmen & Datenstrukturen"}],
                        "events":   [{"id": "evt_001", "title": "Campus Run 5K"}],
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
    x_user_id: str | None = Header(default=None, alias="X-User-ID", description="Firebase UID des Nutzers"),
) -> dict[str, Any]:
    """Gibt gefilterte Vorlesungen und Events zurück.

    Metadaten (courses_of_study, semesters, event_groups) kommen einmalig von `GET /api/v1/settings`.
    Alle Filter-Parameter sind optional und kombinierbar.
    """
    try:
        db = mongo_client.get_db()

        # Decide which collections to query based on which filters are active.
        # Lecture-only params: course, semester, professor, room, recurrence
        # Event-only params:   event_group, public_only
        # Shared params:       building, date_from, date_to
        has_lec_filter = bool(course or semester or professor or room or recurrence)
        has_evt_filter = bool(event_group or public_only)
        # If only one side's filters are active, skip the other side entirely.
        skip_lectures = has_evt_filter and not has_lec_filter
        skip_events = has_lec_filter and not has_evt_filter

        # ── Lecture-Query aufbauen ──────────────────────────────────────
        lectures: list[dict] = []
        if not skip_lectures:
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
            lectures = [_lecture_to_frontend(lec) for lec in serialize_docs(list(db.lectures.find(lec_query).limit(limit_lectures)))]

        # ── Event-Query aufbauen ────────────────────────────────────────
        events: list[dict] = []
        if not skip_events:
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
            raw_events = list(db.events.find(evt_query).sort("start_time", 1).limit(limit_events))

            # Fetch savedEventIds from user settings
            saved_event_ids: list[str] = []
            settings_uid = x_user_id or "default"
            try:
                settings_doc = db.settings.find_one({"_id": settings_uid})
                if settings_doc:
                    saved_event_ids = settings_doc.get("savedEventIds", [])
            except Exception as e:
                logger.warning(f"Error fetching settings for {settings_uid} in timetable: {e}")

            # Ensure saved events are included
            if saved_event_ids:
                fetched_ids = {str(e.get("_id", "")) for e in raw_events}
                missing_ids = [eid for eid in saved_event_ids if eid not in fetched_ids]

                if missing_ids:
                    object_ids = []
                    for eid in missing_ids:
                        try:
                            object_ids.append(ObjectId(eid))
                        except Exception:
                            object_ids.append(eid)
                    
                    missing_events = list(db.events.find({"_id": {"$in": object_ids}}))
                    raw_events.extend(missing_events)

            raw_events_serialized = serialize_docs(raw_events)
            mock_rooms = list(db.rooms.find(
                {"room_number": {"$exists": True}, "building_id": {"$exists": True}},
                {"room_number": 1, "building_id": 1, "_id": 0},
            ))
            events = [_event_to_frontend(e, mock_rooms or None) for e in raw_events_serialized]

        # Fetch study programs from DB for courses_of_study
        db = mongo_client.get_db()
        study_progs = serialize_docs(list(db.studiengaenge.find().sort("code", 1)))
        courses_of_study = [
            {"id": prog.get("code"), "label": prog.get("name", prog.get("code"))}
            for prog in study_progs
        ]

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
