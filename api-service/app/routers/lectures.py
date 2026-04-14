"""Lectures router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.lecture import LectureResponse
from app.utils import serialize_doc, serialize_docs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lectures", tags=["lectures"])


@router.get(
    "",
    response_model=list[LectureResponse],
    summary="Alle Vorlesungen abrufen",
    response_description="Liste der gefilterten Vorlesungen",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "_id": "6623a1f2e4b0a1c2d3e4f5a6",
                            "lecture_id": "INF-2024-001",
                            "room_id": "Z106",
                            "studiengang_id": "INF",
                            "professor": "Prof. Dr. Müller",
                            "module_name": "Algorithmen und Datenstrukturen",
                            "start_time": "2024-04-15T08:00:00",
                            "end_time": "2024-04-15T09:30:00",
                            "day_of_week": "Monday",
                            "duration_minutes": 90,
                            "semester": "SS2024",
                        }
                    ]
                }
            }
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def get_lectures(
    room_id: str | None = Query(None, description="Filtert nach Raum-ID (z. B. `Z106`)"),
    studiengang_id: str | None = Query(None, description="Filtert nach Studiengangs-ID (z. B. `INF`)"),
    date_from: str | None = Query(None, description="Startdatum des Zeitraums im ISO-8601-Format (z. B. `2024-04-15T00:00:00`)"),
    date_to: str | None = Query(None, description="Enddatum des Zeitraums im ISO-8601-Format (z. B. `2024-04-19T23:59:59`)"),
    skip: int = Query(0, ge=0, description="Anzahl der zu überspringenden Einträge (Pagination)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximale Anzahl der zurückgegebenen Einträge (max. 1000)"),
) -> list[LectureResponse]:
    """Gibt alle Vorlesungen zurück, optional gefiltert nach Raum, Studiengang und Zeitraum.

    Unterstützt Pagination über `skip` und `limit`.
    """
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {}

        if room_id:
            query["room_id"] = room_id
        if studiengang_id:
            query["studiengang_id"] = studiengang_id
        if date_from or date_to:
            time_query: dict[str, Any] = {}
            if date_from:
                time_query["$gte"] = date_from
            if date_to:
                time_query["$lte"] = date_to
            query["start_time"] = time_query

        lectures = serialize_docs(list(db.lectures.find(query).skip(skip).limit(limit)))
        return lectures

    except Exception as e:
        logger.error(f"Error fetching lectures: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get(
    "/{lecture_id}",
    response_model=LectureResponse,
    summary="Einzelne Vorlesung abrufen",
    response_description="Die gefundene Vorlesung",
    responses={
        404: {"description": "Vorlesung nicht gefunden"},
        500: {"description": "Datenbankfehler"},
    },
)
async def get_lecture(
    lecture_id: str,
) -> LectureResponse:
    """Gibt eine einzelne Vorlesung anhand ihrer `lecture_id` zurück."""
    try:
        db = mongo_client.get_db()
        lecture = db.lectures.find_one({"lecture_id": lecture_id})

        if not lecture:
            raise HTTPException(
                status_code=404,
                detail="Lecture not found",
            )

        return serialize_doc(lecture)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.post(
    "",
    response_model=dict[str, str],
    summary="Vorlesung anlegen (Admin)",
    response_description="ID der neu erstellten Vorlesung",
    responses={
        200: {
            "content": {"application/json": {"example": {"id": "6623a1f2e4b0a1c2d3e4f5a6"}}}
        },
        500: {"description": "Datenbankfehler"},
    },
)
async def create_lecture(
    lecture: LectureResponse,
) -> dict[str, str]:
    """Legt eine neue Vorlesung in der Datenbank an.

    > **Hinweis:** Dieser Endpunkt ist für den internen Admin-Gebrauch vorgesehen.
    > Vorlesungsdaten werden in der Regel automatisch durch den Scraper befüllt.
    """
    try:
        db = mongo_client.get_db()
        result = db.lectures.insert_one(lecture.dict(exclude_unset=True))
        return {"id": str(result.inserted_id)}

    except Exception as e:
        logger.error(f"Error creating lecture: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e
