"""Events router for CampusNow REST API."""

import logging
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.event import EventCreate, EventResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/events", tags=["events"])


def _serialize(doc: dict) -> dict:
    """Konvertiert MongoDB-ObjectId zu String."""
    if doc and "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


@router.get(
    "",
    response_model=list[EventResponse],
    summary="Alle Events abrufen",
    response_description="Liste der gefilterten Campus-Events",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "6623a1f2e4b0a1c2d3e4f5a6",
                            "title": "Campusfest Sommersemester 2024",
                            "description": "Das jährliche Campusfest mit Live-Musik und Essen.",
                            "category": "Kultur",
                            "start_time": "2024-06-20T14:00:00",
                            "end_time": "2024-06-20T22:00:00",
                            "building_id": "G2",
                            "room_id": None,
                            "location_text": "Außengelände Gebäude G2",
                            "organizer": "Studentenwerk Aalen",
                            "is_public": True,
                            "image_url": None,
                            "created_at": "2024-05-01T10:00:00",
                            "updated_at": None,
                        }
                    ]
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_events(
    category: str | None = Query(
        None,
        description="Filtert nach Kategorie: `Vortrag`, `Sport`, `Kultur`, `Mensa`, `Hochschule`, `Sonstiges`",
    ),
    building_id: str | None = Query(None, description="Filtert nach Gebäude-ID (z. B. `G2`)"),
    date_from: str | None = Query(
        None,
        description="Nur Events ab diesem Datum (ISO 8601, z. B. `2024-06-01T00:00:00`)",
    ),
    date_to: str | None = Query(
        None,
        description="Nur Events bis zu diesem Datum (ISO 8601)",
    ),
    public_only: bool = Query(
        False,
        description="Wenn `true`, werden nur öffentliche Events (Gäste-Modus) zurückgegeben",
    ),
    skip: int = Query(0, ge=0, description="Pagination: Einträge überspringen"),
    limit: int = Query(50, ge=1, le=200, description="Maximale Anzahl der Ergebnisse"),
) -> list[EventResponse]:
    """Gibt Campus-Events zurück, optional gefiltert nach Kategorie, Gebäude und Zeitraum.

    Über `public_only=true` können Events ohne Login (Gäste-Modus) abgerufen werden.
    """
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {}

        if category:
            query["category"] = category
        if building_id:
            query["building_id"] = building_id
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


@router.get(
    "/upcoming",
    response_model=list[EventResponse],
    summary="Kommende Events (nächste 7 Tage)",
    response_description="Events der nächsten 7 Tage, sortiert nach Startzeit",
    responses={
        200: {"description": "Liste der bevorstehenden Events"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_upcoming_events(
    days: int = Query(7, ge=1, le=90, description="Zeitraum in Tagen ab heute (max. 90)"),
    public_only: bool = Query(False, description="Nur öffentliche Events zurückgeben"),
) -> list[EventResponse]:
    """Gibt alle Events zurück, die in den nächsten `days` Tagen beginnen."""
    try:
        db = mongo_client.get_db()
        now = datetime.now()
        until = now + timedelta(days=days)

        query: dict[str, Any] = {
            "start_time": {
                "$gte": now.isoformat(),
                "$lte": until.isoformat(),
            }
        }
        if public_only:
            query["is_public"] = True

        events = [
            _serialize(e)
            for e in db.events.find(query).sort("start_time", 1).limit(50)
        ]
        return events

    except Exception as e:
        logger.error(f"Error fetching upcoming events: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{event_id}",
    response_model=EventResponse,
    summary="Einzelnes Event abrufen",
    response_description="Das gefundene Event",
    responses={
        404: {"description": "Event nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_event(event_id: str) -> EventResponse:
    """Gibt ein einzelnes Event anhand seiner ID zurück."""
    try:
        db = mongo_client.get_db()
        event = db.events.find_one({"_id": ObjectId(event_id)})

        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        return _serialize(event)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "",
    response_model=dict[str, str],
    summary="Event anlegen",
    response_description="ID des neu erstellten Events",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"id": "6623a1f2e4b0a1c2d3e4f5a6"}}
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def create_event(event: EventCreate) -> dict[str, str]:
    """Legt ein neues Campus-Event an.

    Events können einer Gebäude-ID, einer Raum-ID oder einem Freitext-Ort zugeordnet werden.
    Öffentliche Events (`is_public: true`) sind ohne Login sichtbar.
    """
    try:
        db = mongo_client.get_db()
        doc = event.model_dump()
        doc["created_at"] = datetime.now()
        doc["updated_at"] = None

        # Datetimes zu ISO-Strings für konsistente Abfragen
        doc["start_time"] = doc["start_time"].isoformat()
        doc["end_time"] = doc["end_time"].isoformat()

        result = db.events.insert_one(doc)
        return {"id": str(result.inserted_id)}

    except Exception as e:
        logger.error(f"Error creating event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.put(
    "/{event_id}",
    response_model=dict[str, str],
    summary="Event aktualisieren",
    response_description="Bestätigung der Aktualisierung",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"message": "Event updated successfully"}}
            }
        },
        404: {"description": "Event nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def update_event(event_id: str, event: EventCreate) -> dict[str, str]:
    """Aktualisiert ein bestehendes Event vollständig."""
    try:
        db = mongo_client.get_db()
        doc = event.model_dump()
        doc["updated_at"] = datetime.now()
        doc["start_time"] = doc["start_time"].isoformat()
        doc["end_time"] = doc["end_time"].isoformat()

        result = db.events.update_one(
            {"_id": ObjectId(event_id)},
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
    response_model=dict[str, str],
    summary="Event löschen",
    response_description="Bestätigung der Löschung",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"message": "Event deleted successfully"}}
            }
        },
        404: {"description": "Event nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def delete_event(event_id: str) -> dict[str, str]:
    """Löscht ein Event anhand seiner ID."""
    try:
        db = mongo_client.get_db()
        result = db.events.delete_one({"_id": ObjectId(event_id)})

        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Event not found")

        return {"message": "Event deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting event: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
