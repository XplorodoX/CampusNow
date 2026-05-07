"""Buildings router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.building import BuildingResponse
from app.utils import serialize_doc, serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/buildings", tags=["buildings"])


@router.get(
    "",
    response_model=list[BuildingResponse],
    summary="Alle Gebäude abrufen",
    response_description="Liste aller Gebäude auf dem Campus",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "G2",
                            "code": "G2",
                            "name": "Gebäude G2",
                            "campus": "Burren",
                            "address": "Beethovenstr. 1, 73430 Aalen",
                            "floors": [0, 1, 2],
                            "street_view_enabled": True,
                            "room_count": 18,
                            "last_scraped": "2024-04-15T06:00:00",
                            "created_at": "2024-01-01T00:00:00",
                        }
                    ]
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_buildings(
    campus: str | None = Query(
        None,
        description="Filtert nach Campus-Standort: `Main` oder `Burren`",
    ),
    skip: int = Query(0, ge=0, description="Anzahl der zu überspringenden Einträge"),
    limit: int = Query(100, ge=1, le=500, description="Maximale Anzahl der Ergebnisse"),
) -> list[BuildingResponse]:
    """Gibt alle Gebäude der HS Aalen zurück, optional gefiltert nach Campus-Standort."""
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {}

        if campus:
            query["campus"] = campus

        buildings = serialize_docs(list(db.buildings.find(query).skip(skip).limit(limit)))
        return buildings

    except Exception as e:
        logger.error(f"Error fetching buildings: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{building_id}",
    response_model=BuildingResponse,
    summary="Einzelnes Gebäude abrufen",
    response_description="Das gefundene Gebäude mit allen Details",
    responses={
        404: {"description": "Gebäude nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_building(building_id: str) -> BuildingResponse:
    """Gibt ein einzelnes Gebäude anhand seines Kürzels zurück (z. B. `G2`, `H`, `Z`)."""
    try:
        db = mongo_client.get_db()
        building = db.buildings.find_one({"_id": building_id})

        if not building:
            raise HTTPException(status_code=404, detail="Building not found")

        return building

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching building: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{building_id}/rooms",
    response_model=list[dict[str, Any]],
    summary="Räume eines Gebäudes",
    response_description="Alle Räume die zu diesem Gebäude gehören",
    responses={
        404: {"description": "Gebäude nicht gefunden oder keine Räume vorhanden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_building_rooms(
    building_id: str,
    floor: int | None = Query(None, description="Filtert nach Stockwerk"),
) -> list[dict[str, Any]]:
    """Gibt alle Räume eines Gebäudes zurück, optional gefiltert nach Stockwerk."""
    try:
        db = mongo_client.get_db()

        # Prüfen ob Gebäude existiert
        building = db.buildings.find_one({"_id": building_id})
        if not building:
            raise HTTPException(status_code=404, detail="Building not found")

        query: dict[str, Any] = {"building_id": building_id}
        if floor is not None:
            query["floor"] = floor

        rooms = serialize_docs(list(db.rooms.find(query)))

        if not rooms:
            raise HTTPException(
                status_code=404,
                detail="No rooms found for this building",
            )

        return rooms

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching rooms for building: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/{building_id}/schedule",
    response_model=list[dict[str, Any]],
    summary="Belegungsplan eines Gebäudes",
    response_description="Alle Vorlesungen die in Räumen dieses Gebäudes stattfinden",
    responses={
        404: {"description": "Gebäude nicht gefunden oder keine Vorlesungen"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_building_schedule(building_id: str) -> list[dict[str, Any]]:
    """Gibt alle Vorlesungen aller Räume eines Gebäudes zurück."""
    try:
        db = mongo_client.get_db()

        building = db.buildings.find_one({"_id": building_id})
        if not building:
            raise HTTPException(status_code=404, detail="Building not found")

        # Alle room_ids des Gebäudes holen
        room_ids = [
            r["room_id"]
            for r in db.rooms.find({"building_id": building_id}, {"room_id": 1})
            if "room_id" in r
        ]

        if not room_ids:
            raise HTTPException(
                status_code=404,
                detail="No rooms found for this building",
            )

        lectures = serialize_docs(list(db.lectures.find({"room_id": {"$in": room_ids}})))

        if not lectures:
            raise HTTPException(
                status_code=404,
                detail="No lectures found for this building",
            )

        return lectures

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching schedule for building: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
