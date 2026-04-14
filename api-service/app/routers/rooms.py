"""Rooms router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.room import RoomResponse
from app.utils import serialize_doc, serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


@router.get(
    "",
    response_model=list[RoomResponse],
    summary="Alle Räume abrufen",
    response_description="Liste der gefilterten Räume",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "Z106",
                            "room_number": "Z106",
                            "floor": 1,
                            "capacity": 40,
                            "building": "Z",
                            "has_video": True,
                            "has_projector": True,
                            "street_view_enabled": True,
                            "room_image_360": {
                                "image_paths": ["2024-04-15-083000-panorama.jpg"],
                                "latest_update": "2024-04-15T08:30:00",
                                "url_prefix": "/api/v1/images/rooms/Z106/",
                            },
                            "created_at": "2024-01-01T00:00:00",
                        }
                    ]
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_rooms(
    floor: int | None = Query(None, description="Filtert nach Stockwerk (z. B. `1` für erstes OG)"),
    search: str | None = Query(None, description="Suche im Raumnamen (Groß-/Kleinschreibung egal, z. B. `Z1`)"),
    skip: int = Query(0, ge=0, description="Anzahl der zu überspringenden Einträge (Pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl der zurückgegebenen Einträge (max. 1000)"),
) -> list[RoomResponse]:
    """Gibt alle Räume der HS Aalen zurück, optional gefiltert nach Stockwerk oder Raumnummer."""
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {}

        if floor is not None:
            query["floor"] = floor
        if search:
            query["room_number"] = {
                "$regex": search,
                "$options": "i",
            }

        rooms = serialize_docs(list(db.rooms.find(query).skip(skip).limit(limit)))
        return rooms

    except Exception as e:
        logger.error(f"Error fetching rooms: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get(
    "/{room_id}",
    response_model=RoomResponse,
    summary="Einzelnen Raum abrufen",
    response_description="Der gefundene Raum mit allen Details",
    responses={
        404: {"description": "Raum nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_room(room_id: str) -> RoomResponse:
    """Gibt einen einzelnen Raum anhand seiner ID zurück (z. B. `Z106`)."""
    try:
        db = mongo_client.get_db()
        room = db.rooms.find_one({"_id": room_id})

        if not room:
            raise HTTPException(
                status_code=404,
                detail="Room not found",
            )

        return room

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching room: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get(
    "/{room_id}/schedule",
    response_model=list[dict[str, Any]],
    summary="Belegungsplan eines Raums",
    response_description="Liste aller Vorlesungen die in diesem Raum stattfinden",
    responses={
        404: {"description": "Keine Vorlesungen für diesen Raum gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_room_schedule(
    room_id: str,
) -> list[dict[str, Any]]:
    """Gibt alle Vorlesungen zurück, die in einem bestimmten Raum stattfinden."""
    try:
        db = mongo_client.get_db()
        lectures = serialize_docs(list(db.lectures.find({"room_id": room_id})))

        if not lectures:
            raise HTTPException(
                status_code=404,
                detail="No lectures found for this room",
            )

        return lectures

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
