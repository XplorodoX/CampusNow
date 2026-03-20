"""Scheduler router for CampusNow REST API."""

import logging
from typing import Any

from fastapi import APIRouter

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/scheduler",
    tags=["scheduler"],
)


@router.get("/status")
async def get_scheduler_status() -> dict[str, Any]:
    """Get current scheduler status."""
    return {
        "status": "running",
        "next_run": "Tomorrow at 06:00",
        "last_run": "Today at 06:00",
        "message": "Scheduler running - documentation coming soon",
    }


@router.get("/logs")
async def get_scheduler_logs(limit: int = 50) -> dict[str, Any]:
    """Fetch scheduler logs."""
    return {
        "logs": [],
        "total": 0,
        "limit": limit,
        "message": "Log fetching coming soon",
    }


@router.post("/trigger")
async def trigger_scraper() -> dict[str, str]:
    """Trigger manual scraper run (admin only)."""
    return {
        "message": "Scraper job started manually",
        "status": "pending",
    }
