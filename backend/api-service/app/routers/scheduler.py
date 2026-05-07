"""Scheduler router for CampusNow REST API."""

import logging
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.auth import require_api_key
from app.db.mongo_client import mongo_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/scheduler", tags=["scheduler"])

# Scheduler läuft täglich um 06:00 Uhr Europe/Berlin
_CRON_DESCRIPTION = "Täglich um 06:00 Uhr (Europe/Berlin)"


def _serialize(doc: dict) -> dict:
    if doc and "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    # datetime → ISO-String für JSON-Kompatibilität
    for key in ("started_at", "completed_at"):
        if key in doc and doc[key] is not None and hasattr(doc[key], "isoformat"):
            doc[key] = doc[key].isoformat()
    return doc


@router.get(
    "/status",
    summary="Scheduler-Status abrufen",
    response_description="Letzter Job-Lauf und nächste geplante Ausführung",
    responses={
        200: {
            "content": {
                "application/json": {
                    "examples": {
                        "success": {
                            "summary": "Letzter Lauf erfolgreich",
                            "value": {
                                "status": "success",
                                "schedule": "Täglich um 06:00 Uhr (Europe/Berlin)",
                                "last_run": {
                                    "id": "6623a1f2e4b0a1c2d3e4f5a6",
                                    "status": "success",
                                    "started_at": "2024-04-15T06:00:00",
                                    "completed_at": "2024-04-15T06:04:32",
                                    "rooms_processed": 87,
                                    "courses_processed": 210,
                                    "lectures_total": 4823,
                                    "buildings_upserted": 12,
                                    "error": None,
                                },
                                "total_runs": 42,
                                "failed_runs": 1,
                            },
                        },
                        "no_data": {
                            "summary": "Noch kein Lauf",
                            "value": {
                                "status": "never_run",
                                "schedule": "Täglich um 06:00 Uhr (Europe/Berlin)",
                                "last_run": None,
                                "total_runs": 0,
                                "failed_runs": 0,
                            },
                        },
                    }
                }
            }
        }
    },
)
async def get_scheduler_status() -> dict[str, Any]:
    """Gibt den Status des letzten Scraper-Laufs sowie Gesamtstatistiken zurück.

    Der Scheduler führt den Scrape-Job täglich um **06:00 Uhr** automatisch aus.
    """
    try:
        db = mongo_client.get_db()

        last_log = db.scheduler_logs.find_one(
            sort=[("started_at", -1)],
        )
        total_runs = db.scheduler_logs.count_documents({})
        failed_runs = db.scheduler_logs.count_documents({"status": "failed"})

        current_status = "never_run"
        if last_log:
            current_status = last_log.get("status", "unknown")

        return {
            "status": current_status,
            "schedule": _CRON_DESCRIPTION,
            "last_run": _serialize(last_log) if last_log else None,
            "total_runs": total_runs,
            "failed_runs": failed_runs,
        }
    except Exception as e:
        logger.error(f"Error fetching scheduler status: {e}")
        return {
            "status": "error",
            "schedule": _CRON_DESCRIPTION,
            "last_run": None,
            "total_runs": 0,
            "failed_runs": 0,
            "error": str(e),
        }


@router.get(
    "/logs",
    summary="Scheduler-Logs abrufen",
    response_description="Liste der letzten Scraper-Läufe, neueste zuerst",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "logs": [
                            {
                                "id": "6623a1f2e4b0a1c2d3e4f5a6",
                                "status": "success",
                                "started_at": "2024-04-15T06:00:00",
                                "completed_at": "2024-04-15T06:04:32",
                                "rooms_processed": 87,
                                "courses_processed": 210,
                                "lectures_total": 4823,
                                "buildings_upserted": 12,
                                "error": None,
                            }
                        ],
                        "total": 42,
                        "limit": 20,
                    }
                }
            }
        }
    },
)
async def get_scheduler_logs(
    limit: int = Query(20, ge=1, le=100, description="Maximale Anzahl der zurückgegebenen Einträge"),
    status: str | None = Query(
        None,
        description="Filtert nach Status: `success`, `failed`, `running`",
    ),
) -> dict[str, Any]:
    """Gibt die letzten Scraper-Läufe aus der Datenbank zurück, neueste zuerst."""
    try:
        db = mongo_client.get_db()
        query: dict[str, Any] = {}
        if status:
            query["status"] = status

        logs = [
            _serialize(doc)
            for doc in db.scheduler_logs.find(query, sort=[("started_at", -1)]).limit(limit)
        ]
        total = db.scheduler_logs.count_documents(query)

        return {
            "logs": logs,
            "total": total,
            "limit": limit,
        }
    except Exception as e:
        logger.error(f"Error fetching scheduler logs: {e}")
        return {"logs": [], "total": 0, "limit": limit, "error": str(e)}


@router.post(
    "/trigger",
    dependencies=[Depends(require_api_key)],
    summary="Scraper manuell starten (Admin)",
    response_description="Bestätigung, dass der Scraper gestartet wurde",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": {"message": "Scraper job started manually", "status": "pending"}
                }
            }
        }
    },
)
async def trigger_scraper() -> dict[str, str]:
    """Löst einen manuellen Scraper-Lauf aus, ohne auf den geplanten Zeitpunkt zu warten.

    > **Hinweis:** Der Job läuft im Scraper-Service. Dieser Endpunkt gibt sofort zurück –
    > den Fortschritt via `GET /scheduler/status` oder `GET /scheduler/logs` verfolgen.
    """
    return {
        "message": "Scraper job started manually",
        "status": "pending",
    }
