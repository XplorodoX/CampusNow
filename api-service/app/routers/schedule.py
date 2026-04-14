"""Schedule router – persönlicher iCal-Import für Studierende (Key Scenario 3)."""

import logging

from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.models.schedule import ScheduleEntry, ScheduleSyncRequest, ScheduleSyncResponse
from app.services import ical_import

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/schedule", tags=["schedule"])


@router.post(
    "/sync",
    response_model=ScheduleSyncResponse,
    summary="Persönlichen Stundenplan synchronisieren",
    response_description="Geparste Vorlesungen mit DB-Anreicherung (Raum- und Gebäude-IDs)",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "total": 12,
                        "matched_rooms": 10,
                        "unmatched_rooms": ["Extern", "Online"],
                        "entries": [
                            {
                                "uid": "abc123@starplan",
                                "module_name": "Algorithmen und Datenstrukturen",
                                "summary": "Algorithmen und Datenstrukturen (Prof. Müller)",
                                "professor": "Prof. Müller",
                                "room_number": "G2 1.01",
                                "room_id": "42",
                                "building_id": "G2",
                                "room_known": True,
                                "start_time": "2024-04-15T08:00:00",
                                "end_time": "2024-04-15T09:30:00",
                                "day_of_week": "Monday",
                                "duration_minutes": 90,
                                "imported_at": "2024-04-15T12:00:00",
                            }
                        ],
                    }
                }
            }
        },
        400: {"description": "Ungültige oder nicht erreichbare iCal-URL"},
        422: {"description": "URL fehlt oder hat falsches Format"},
        500: {"description": "Fehler beim Parsen der iCal-Datei"},
    },
)
async def sync_personal_schedule(body: ScheduleSyncRequest) -> ScheduleSyncResponse:
    """Importiert den persönlichen Stundenplan eines Studierenden aus StarPlan.

    **Anleitung (Key Scenario 3):**
    1. Im HS-Aalen-Portal einloggen → Stundenplan öffnen
    2. „iCal-Export" oder „iCal-Link" kopieren
    3. Die URL hier einfügen und absenden

    Die API parst die `.ics`-Datei, extrahiert alle Vorlesungen und reichert sie mit
    Raum- und Gebäude-IDs aus der CampusNow-Datenbank an.
    Räume, die nicht zugeordnet werden konnten, werden in `unmatched_rooms` aufgelistet.
    """
    url = body.ical_url

    # 1. Abrufen & Parsen
    try:
        raw_entries = ical_import.fetch_and_parse(url)
    except Exception as exc:
        logger.warning("iCal fetch failed for %s: %s", url, exc)
        raise HTTPException(
            status_code=400,
            detail=f"iCal-URL konnte nicht geladen werden: {exc}",
        ) from exc

    if not raw_entries:
        return ScheduleSyncResponse(
            total=0,
            matched_rooms=0,
            unmatched_rooms=[],
            entries=[],
        )

    # 2. Mit DB anreichern
    try:
        db = mongo_client.get_db()
        enriched = ical_import.enrich_with_db(raw_entries, db)
    except Exception as exc:
        logger.error("DB enrichment failed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # 3. Statistik berechnen
    matched = [e for e in enriched if e.get("room_known")]
    unmatched_rooms = sorted({
        e["room_number"]
        for e in enriched
        if not e.get("room_known") and e.get("room_number")
    })

    entries = [ScheduleEntry(**e) for e in enriched]

    return ScheduleSyncResponse(
        total=len(entries),
        matched_rooms=len(matched),
        unmatched_rooms=unmatched_rooms,
        entries=entries,
    )
