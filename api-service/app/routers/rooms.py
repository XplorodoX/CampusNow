"""Rooms router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.db.mongo_client import mongo_client
from app.models.room import RoomResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/rooms", tags=["rooms"])


@router.get("", response_model=list[RoomResponse])
async def get_rooms(
    floor: int | None = Query(None),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
) -> list[RoomResponse]:
    """Fetch all rooms with optional filters.

    Args:
        floor: Filter by floor number
        search: Search room number (case-insensitive)
        skip: Number of records to skip (default: 0)
        limit: Maximum records to return (default: 100, max: 1000)

    Returns:
        List of matching rooms

    Raises:
        HTTPException: 500 if database error occurs
    """
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

        rooms = list(db.rooms.find(query).skip(skip).limit(limit))
        return rooms

    except Exception as e:
        logger.error(f"Error fetching rooms: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e),
        ) from e


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(room_id: str) -> RoomResponse:
    """Fetch room details by ID.

    Args:
        room_id: The room ID to fetch

    Returns:
        The matching room

    Raises:
        HTTPException: 404 if room not found, 500 if error
    """
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


@router.get("/{room_id}/schedule", response_model=list[dict[str, Any]])
async def get_room_schedule(
    room_id: str,
) -> list[dict[str, Any]]:
    """Fetch schedule for a specific room.

    Args:
        room_id: The room ID to fetch schedule for

    Returns:
        List of lectures for the room

    Raises:
        HTTPException: 404 if no lectures found, 500 if error
    """
    try:
        db = mongo_client.get_db()
        lectures = list(db.lectures.find({"room_id": room_id}))

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
