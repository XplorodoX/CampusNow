"""Studiengaenge (courses) router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.models.studiengang import StuDiengangResponse
from app.utils import serialize_doc, serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/studiengaenge", tags=["studiengaenge"])


def _serialize_studiengang_document(document: dict[str, Any]) -> dict[str, Any]:
    """Convert MongoDB-specific values into API-friendly primitives."""
    if "_id" in document:
        document["_id"] = str(document["_id"])
    return document


@router.get(
    "",
    response_model=list[StuDiengangResponse],
    summary="Alle Studiengänge abrufen",
    response_description="Liste aller verfügbaren Studiengänge",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "INF-B-6",
                            "name": "Informatik",
                            "code": "INF",
                            "semester": "6",
                            "program_code": "INF-B",
                            "program_name": "Bachelor Informatik",
                            "lecture_count": 12,
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
async def get_studiengaenge() -> list[StuDiengangResponse]:
    """Gibt alle Studiengänge zurück, die im STARplan-System der HS Aalen hinterlegt sind."""
    try:
        db = mongo_client.get_db()
        studiengaenge = [
            _serialize_studiengang_document(studiengang)
            for studiengang in db.studiengaenge.find()
        ]
        return studiengaenge

    except Exception as e:
        logger.error(f"Error fetching Studiengänge: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get(
    "/{studiengang_id}",
    response_model=StuDiengangResponse,
    summary="Einzelnen Studiengang abrufen",
    response_description="Der gefundene Studiengang",
    responses={
        404: {"description": "Studiengang nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengang(
    studiengang_id: str,
) -> StuDiengangResponse:
    """Gibt einen einzelnen Studiengang anhand seiner ID zurück (z. B. `INF-B-6`)."""
    try:
        db = mongo_client.get_db()
        studiengang = db.studiengaenge.find_one({"_id": studiengang_id})

        if not studiengang:
            raise HTTPException(
                status_code=404,
                detail="Studiengang not found",
            )

        return _serialize_studiengang_document(studiengang)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Studiengang: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get(
    "/{studiengang_id}/lectures",
    response_model=list[dict[str, Any]],
    summary="Vorlesungen eines Studiengangs abrufen",
    response_description="Liste aller Vorlesungen für diesen Studiengang",
    responses={
        404: {"description": "Keine Vorlesungen für diesen Studiengang gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_studiengang_lectures(
    studiengang_id: str,
) -> list[dict[str, Any]]:
    """Gibt alle Vorlesungen zurück, die einem bestimmten Studiengang zugeordnet sind."""
    try:
        db = mongo_client.get_db()
        lectures = serialize_docs(list(db.lectures.find({"studiengang_id": studiengang_id})))

        if not lectures:
            raise HTTPException(
                status_code=404,
                detail="No lectures found for this Studiengang",
            )

        return lectures

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lectures: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
