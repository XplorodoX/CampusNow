"""Rooms router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.room import RoomResponse
from app.utils import serialize_docs

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
    building: str | None = Query(None, description="Filtert nach Gebäude-Kürzel oder Building-ID (z. B. `G2`)"),
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
        if building:
            query["$or"] = [{"building_id": building}, {"building": building}]

        rooms = serialize_docs(list(db.rooms.find(query).skip(skip).limit(limit)))
        return rooms

    except Exception as e:
        logger.error(f"Error fetching rooms: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
