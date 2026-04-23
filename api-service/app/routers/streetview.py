"""Street View Graph router – 360°-Navigationsgraph für Räume/Gebäude."""

import logging
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.auth import require_api_key
from app.db.mongo_client import mongo_client
from app.models.streetview import StreetViewGraph, StreetViewGraphCreate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/streetview", tags=["streetview"])


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc


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


@router.get(
    "/graph/room/{room_id}",
    response_model=StreetViewGraph,
    summary="Navigationsgraph für einen Raum",
    response_description="Der 360°-Navigationsgraph für den angegebenen Raum",
    responses={
        404: {"description": "Kein Graph für diesen Raum gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_room_graph(room_id: str) -> StreetViewGraph:
    """Gibt den 360°-Navigationsgraphen für einen bestimmten Raum zurück."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"room_id": room_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No street view graph found for room {room_id}",
            )
        return doc["graph"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching street view graph for room {room_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/graph/building/{building_id}",
    response_model=StreetViewGraph,
    summary="Navigationsgraph für ein Gebäude",
    response_description="Der 360°-Navigationsgraph für das angegebene Gebäude",
    responses={
        404: {"description": "Kein Graph für dieses Gebäude gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_building_graph(building_id: str) -> StreetViewGraph:
    """Gibt den 360°-Navigationsgraphen für ein bestimmtes Gebäude zurück."""
    try:
        db = mongo_client.get_db()
        doc = db.streetview_graphs.find_one({"building_id": building_id})
        if not doc:
            raise HTTPException(
                status_code=404,
                detail=f"No street view graph found for building {building_id}",
            )
        return doc["graph"]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching street view graph for building {building_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post(
    "/graph",
    dependencies=[Depends(require_api_key)],
    response_model=dict[str, str],
    summary="Navigationsgraph speichern (Admin)",
    response_description="ID des gespeicherten Graphen",
    responses={
        200: {
            "content": {
                "application/json": {"example": {"id": "6623a1f2e4b0a1c2d3e4f5a6"}}
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def save_graph(body: StreetViewGraphCreate) -> dict[str, str]:
    """Speichert einen neuen 360°-Navigationsgraphen.

    Das Format entspricht exakt `street_view_graph.json`.
    Ein bestehender Graph für denselben `room_id` oder `building_id` wird automatisch ersetzt.

    **Pflichtfelder im Graph:**
    - `startNode` – ID des Startknotens
    - `nodes[]` – Knoten mit `id`, `image`, `exits` und optionalen `spots`
    """
    try:
        db = mongo_client.get_db()
        from datetime import datetime

        filter_q: dict[str, Any] = {}
        if body.room_id:
            filter_q["room_id"] = body.room_id
        elif body.building_id:
            filter_q["building_id"] = body.building_id

        doc: dict[str, Any] = {
            "graph": body.graph.model_dump(),
            "created_at": datetime.now(),
        }
        if body.room_id:
            doc["room_id"] = body.room_id
        if body.building_id:
            doc["building_id"] = body.building_id

        if filter_q:
            result = db.streetview_graphs.replace_one(filter_q, doc, upsert=True)
            inserted_id = str(result.upserted_id or filter_q.get("room_id") or filter_q.get("building_id"))
        else:
            result = db.streetview_graphs.insert_one(doc)
            inserted_id = str(result.inserted_id)

        return {"id": inserted_id}

    except Exception as e:
        logger.error(f"Error saving street view graph: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
