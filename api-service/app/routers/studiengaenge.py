"""Studiengaenge (courses) router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.db.mongo_client import mongo_client
from app.models.studiengang import StuDiengangResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/studiengaenge", tags=["studiengaenge"])


@router.get("", response_model=list[StuDiengangResponse])
async def get_studiengaenge() -> list[StuDiengangResponse]:
    """Fetch all courses/study programs.

    Returns:
        List of all available courses

    Raises:
        HTTPException: 500 if database error occurs
    """
    try:
        db = mongo_client.get_db()
        studiengaenge = list(db.studiengaenge.find())
        return studiengaenge

    except Exception as e:
        logger.error(f"Error fetching Studiengänge: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get("/{studiengang_id}", response_model=StuDiengangResponse)
async def get_studiengang(
    studiengang_id: str,
) -> StuDiengangResponse:
    """Fetch a single course/study program by ID.

    Args:
        studiengang_id: The course ID to fetch

    Returns:
        The matching course

    Raises:
        HTTPException: 404 if not found, 500 if error
    """
    try:
        db = mongo_client.get_db()
        studiengang = db.studiengaenge.find_one({"_id": studiengang_id})

        if not studiengang:
            raise HTTPException(
                status_code=404,
                detail="Studiengang not found",
            )

        return studiengang

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Studiengang: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get("/{studiengang_id}/lectures", response_model=list[dict[str, Any]])
async def get_studiengang_lectures(
    studiengang_id: str,
) -> list[dict[str, Any]]:
    """Fetch all lectures for a course/study program.

    Args:
        studiengang_id: The course ID to fetch lectures for

    Returns:
        List of lectures for the course

    Raises:
        HTTPException: 404 if no lectures found, 500 if error
    """
    try:
        db = mongo_client.get_db()
        lectures = list(db.lectures.find({"studiengang_id": studiengang_id}))

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
