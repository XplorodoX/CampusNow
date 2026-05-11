"""Buildings router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.building import BuildingResponse
from app.utils import serialize_docs

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
