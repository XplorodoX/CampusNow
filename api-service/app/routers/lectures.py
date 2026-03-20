"""Lectures router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.lecture import LectureResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lectures", tags=["lectures"])


@router.get("", response_model=list[LectureResponse])
async def get_lectures(
    room_id: str | None = Query(None),
    studiengang_id: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[LectureResponse]:
    """Fetch all lectures with optional filters.

    Args:
        room_id: Filter by room ID
        studiengang_id: Filter by course/program ID
        date_from: Filter start date (ISO 8601)
        date_to: Filter end date (ISO 8601)
        skip: Number of records to skip (default: 0)
        limit: Maximum records to return (default: 100, max: 1000)

    Returns:
        List of matching lectures

    Raises:
        HTTPException: 500 if database error occurs
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

        lectures = list(db.lectures.find(query).skip(skip).limit(limit))
        return lectures

    except Exception as e:
        logger.error(f"Error fetching lectures: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get("/{lecture_id}", response_model=LectureResponse)
async def get_lecture(
    lecture_id: str,
) -> LectureResponse:
    """Fetch a single lecture by ID.

    Args:
        lecture_id: The lecture ID to fetch

    Returns:
        The matching lecture

    Raises:
        HTTPException: 404 if lecture not found, 500 if error
    """
    try:
        db = mongo_client.get_db()
        lecture = db.lectures.find_one({"lecture_id": lecture_id})

        if not lecture:
            raise HTTPException(
                status_code=404,
                detail="Lecture not found",
            )

        return lecture

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lecture: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.post("", response_model=dict[str, str])
async def create_lecture(
    lecture: LectureResponse,
) -> dict[str, str]:
    """Create a new lecture (admin only).

    Args:
        lecture: The lecture data to create

    Returns:
        Dict with the created lecture ID

    Raises:
        HTTPException: 500 if database error occurs
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
