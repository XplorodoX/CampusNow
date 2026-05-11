"""Events router for CampusNow REST API."""

import logging
from datetime import datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_api_key
from app.db.mongo_client import mongo_client
from app.models.event import EventCreate, EventResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])

_EVENT_GROUP_IDS = "`sports` · `workshops` · `academic` · `culture` · `alumni` · `international` · `career` · `social`"


def _parse_object_id(event_id: str) -> ObjectId:
    try:
        return ObjectId(event_id)
    except (InvalidId, Exception):
        raise HTTPException(status_code=404, detail="Event not found")


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


def _resolve_event_times(doc: dict[str, Any]) -> tuple[str, str]:
    start_iso = doc.get("startTime")
    if not start_iso and doc.get("start_time") is not None:
        start_iso = doc["start_time"].isoformat()

    end_iso = doc.get("endTime")
    if not end_iso and doc.get("end_time") is not None:
        end_iso = doc["end_time"].isoformat()

    if not start_iso or not end_iso:
        raise HTTPException(
            status_code=422,
            detail="Both start_time and end_time are required.",
        )

    return start_iso, end_iso


@router.get(
    "",
    response_model=list[EventResponse],
    response_model_exclude_none=True,
    summary="Events abrufen",
    response_description="Liste der Campus-Events, aufsteigend nach Startzeit sortiert",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "6623a1f2e4b0a1c2d3e4f5a6",
                            "title": "Campus Run 5K",
                            "groupId": "sports",
                            "start_time": "2024-06-20T09:00:00",
                            "end_time": "2024-06-20T11:00:00",
                            "building": "G2",
                            "room": "Außengelände",
                            "organizer": "Hochschulsport Aalen",
                            "is_public": True,
                            "image_url": "https://picsum.photos/seed/6623a1f2e4b0a1c2d3e4f5a6/800/450",
                            "detail_url": "https://www.hs-aalen.de/aktuelles/veranstaltungen/campus-run",
                            "description": "Der jährliche Campus-Lauf rund um das Gelände der HS Aalen.",
                            "created_at": "2024-05-01T10:00:00",
                        }
                    ]
                }
            }
        },
        500: {"description": "Interner Datenbankfehler"},
    },
)
async def get_events(
    group_id: str | None = Query(
        None,
        alias="groupId",
        description=f"Filtert nach Event-Gruppe: {_EVENT_GROUP_IDS}",
    ),
    building: str | None = Query(
        None,
        description="Filtert nach Gebäude-Kürzel (exakter Match, z. B. `G2`)",
    ),
    date_from: str | None = Query(
        None,
        description="Nur Events **ab** diesem Datum (ISO 8601, z. B. `2024-06-01` oder `2024-06-01T00:00:00`)",
    ),
    date_to: str | None = Query(
        None,
        description="Nur Events **bis** zu diesem Datum (ISO 8601, z. B. `2024-06-30T23:59:59`)",
    ),
    public_only: bool = Query(
        False,
        description="Wenn `true`, werden nur öffentliche Events zurückgegeben (Gäste-Modus ohne Login)",
    ),
    skip: int = Query(0, ge=0, description="Anzahl Einträge überspringen (Pagination)"),
    limit: int = Query(50, ge=1, le=200, description="Maximale Trefferzahl (1–200, Standard 50)"),
) -> list[EventResponse]:
    """Gibt Campus-Events zurück, optional gefiltert nach Gruppe, Gebäude und Zeitraum.

    Alle Parameter sind optional und frei kombinierbar. Sortierung ist aufsteigend nach `start_time`.

    **Gäste-Modus:** Mit `public_only=true` werden nur Events zurückgegeben, die für nicht eingeloggte
    Nutzer sichtbar sind (`is_public: true`).
    """
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {}

        if group_id:
            query["groupId"] = group_id
        if building:
            query["building"] = building
        if public_only:
            query["is_public"] = True
        if date_from or date_to:
            time_query: dict[str, Any] = {}
            if date_from:
                time_query["$gte"] = date_from
            if date_to:
                time_query["$lte"] = date_to
            query["start_time"] = time_query

        events = [
            _serialize(e)
            for e in db.events.find(query).sort("start_time", 1).skip(skip).limit(limit)
        ]
        return events

    except Exception as e:
        logger.error(f"Error fetching events: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "",
    dependencies=[Depends(require_api_key)],
    response_model=dict[str, str],
    summary="Event anlegen (Admin)",
    response_description="MongoDB-ID des neu erstellten Events",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"id": "6623a1f2e4b0a1c2d3e4f5a6"}
                }
            }
        },
        401: {"description": "Ungültiger oder fehlender API-Key"},
        422: {"description": "start_time oder end_time fehlen"},
        500: {"description": "Interner Datenbankfehler"},
    },
)
async def create_event(event: EventCreate) -> dict[str, str]:
    """Legt ein neues Campus-Event an. Erfordert API-Key-Authentifizierung.

    - `start_time` und `end_time` sind Pflichtfelder.
    - `groupId` sollte einem der definierten Gruppen-IDs entsprechen
      (sports, workshops, academic, culture, alumni, international, career, social).
    - Öffentliche Events (`is_public: true`) sind im Gäste-Modus ohne Login sichtbar.
    - `image_url` wird vom Scraper automatisch gesetzt; fehlt sie, erzeugt das Frontend ein Platzhalterbild.
    """
    try:
        db = mongo_client.get_db()
        doc = event.model_dump()
        start_iso, end_iso = _resolve_event_times(doc)
        doc["created_at"] = datetime.now()
        doc["updated_at"] = None
        doc["start_time"] = start_iso
        doc["end_time"] = end_iso

        result = db.events.insert_one(doc)
        return {"id": str(result.inserted_id)}

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put(
    "/{event_id}",
    dependencies=[Depends(require_api_key)],
    response_model=dict[str, str],
    summary="Event aktualisieren (Admin)",
    response_description="Bestätigung der vollständigen Aktualisierung",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "Event updated successfully"}
                }
            }
        },
        401: {"description": "Ungültiger oder fehlender API-Key"},
        404: {"description": "Event mit dieser ID nicht gefunden"},
        422: {"description": "start_time oder end_time fehlen"},
        500: {"description": "Interner Datenbankfehler"},
    },
)
async def update_event(event_id: str, event: EventCreate) -> dict[str, str]:
    """Überschreibt ein bestehendes Event vollständig (PUT-Semantik).

    Alle Felder des Request-Body ersetzen die gespeicherten Werte.
    `created_at` bleibt erhalten; `updated_at` wird auf die aktuelle Zeit gesetzt.
    """
    try:
        db = mongo_client.get_db()
        doc = event.model_dump()
        start_iso, end_iso = _resolve_event_times(doc)
        doc["updated_at"] = datetime.now()
        doc["start_time"] = start_iso
        doc["end_time"] = end_iso

        result = db.events.update_one(
            {"_id": _parse_object_id(event_id)},
            {"$set": doc},
        )

        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Event not found")

        return {"message": "Event updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete(
    "/{event_id}",
    dependencies=[Depends(require_api_key)],
    response_model=dict[str, str],
    summary="Event löschen (Admin)",
    response_description="Bestätigung der Löschung",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "Event deleted successfully"}
                }
            }
        },
        401: {"description": "Ungültiger oder fehlender API-Key"},
        404: {"description": "Event mit dieser ID nicht gefunden"},
        500: {"description": "Interner Datenbankfehler"},
    },
)
async def delete_event(event_id: str) -> dict[str, str]:
    """Löscht ein Event dauerhaft anhand seiner MongoDB-ID."""
    try:
        db = mongo_client.get_db()
        result = db.events.delete_one({"_id": _parse_object_id(event_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Event not found")

        return {"message": "Event deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
