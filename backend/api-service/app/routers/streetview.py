"""Street View Graph router – 360°-Navigationsgraph des Campus."""

import logging

from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.models.streetview import StreetViewGraph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/streetview", tags=["streetview"])


@router.get(
    "/graph",
    response_model=StreetViewGraph,
    summary="Standard-Navigationsgraph abrufen",
    response_description="Der neueste 360°-Navigationsgraph aus der Datenbank",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "startNode": "node0",
                        "nodes": [
                            {
                                "id": "node0",
                                "image": "assets/images/360-0.JPG",
                                "building": "G2",
                                "room": "G2 0.01",
                                "heading": 12,
                                "exits": {"front": "node1", "right": "node2"},
                                "spots": [
                                    {
                                        "name": "Hinweisschild",
                                        "longitude": 8,
                                        "latitude": 0,
                                        "description": "Wegweiser zu den Hörsälen",
                                    }
                                ],
                            }
                        ],
                    }
                }
            }
        },
        404: {"description": "Kein Graph in der Datenbank vorhanden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_default_graph() -> StreetViewGraph:
    """Gibt den Standard-360°-Navigationsgraphen zurück.

    Entspricht dem Format von `street_view_graph.json`:
    - `startNode`: ID des Startknotens
    - `nodes[]`: Knoten mit Bild, Ausgängen und interaktiven Spots
    """
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one(sort=[("created_at", -1)])
        if not doc:
            raise HTTPException(status_code=404, detail="No street view graph found")
        return doc["graph"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching street view graph: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
