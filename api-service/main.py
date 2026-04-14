#!/usr/bin/env python3
"""Main entry point for CampusNow REST API service."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo_client import mongo_client
from app.routers import (
    buildings,
    events,
    images,
    lectures,
    rooms,
    schedule,
    scheduler,
    settings,
    streetview,
    studiengaenge,
    timetable,
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=os.getenv("API_TITLE", "CampusNow API"),
    description="""
## CampusNow REST API

Interaktive Campus-Navigations- und Stundenplan-API für die **Hochschule Aalen**.

### Frontend-Endpunkte (direkt konsumierbar)

| Endpunkt | Beschreibung | Entspricht |
|---|---|---|
| `GET /api/v1/timetable` | Stundenplan komplett | `timetable.json` |
| `GET /api/v1/streetview/graph` | 360°-Navigationsgraph | `street_view_graph.json` |
| `GET /api/v1/settings` | Nutzereinstellungen | `settings.json` |

### Weitere Funktionen

- **Gebäude** – Alle Gebäude der HS Aalen mit Räumen und Stockwerken
- **Räume** – Raumdaten inkl. Ausstattung, 360°-Bilder und Belegungspläne
- **Studiengänge** – Alle Studiengänge aus STARplan
- **Events** – Campus-Events mit Gäste-Modus (`public_only=true`)
- **iCal-Import** – Persönlichen StarPlan-Link einfügen → Stundenplan sofort verfügbar
- **Scheduler** – Scraper-Status und Logs aus der Datenbank

### Datenquelle

Vorlesungsdaten werden täglich um **06:00 Uhr** automatisch aus dem
[STARplan-System](https://vorlesungen.htw-aalen.de) der HS Aalen gescrapt.
""",
    version=os.getenv("API_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "CampusNow Team",
    },
    license_info={
        "name": "MIT",
    },
    openapi_tags=[
        # ── Frontend-direkte Endpunkte ──────────────────────────────────
        {
            "name": "timetable",
            "description": (
                "**Frontend-Endpunkt.** Liefert Vorlesungen, Events, Studiengänge, Semester und "
                "Event-Gruppen in einem einzigen Call – entspricht exakt `timetable.json`."
            ),
        },
        {
            "name": "streetview",
            "description": (
                "**Frontend-Endpunkt.** 360°-Navigationsgraphen abrufen und speichern. "
                "Entspricht dem Format von `street_view_graph.json` mit Knoten, Ausgängen und Spots."
            ),
        },
        {
            "name": "settings",
            "description": (
                "**Frontend-Endpunkt.** Nutzer-Einstellungen lesen (`GET`), vollständig überschreiben (`PUT`) "
                "oder teilweise aktualisieren (`PATCH`). Entspricht `settings.json`."
            ),
        },
        # ── Kern-Daten ──────────────────────────────────────────────────
        {
            "name": "buildings",
            "description": (
                "Gebäude der HS Aalen. Wird automatisch beim Scraper-Lauf befüllt. "
                "Enthält Stockwerk-Liste, Raum-Anzahl und Campus-Zuordnung (Main / Burren)."
            ),
        },
        {
            "name": "rooms",
            "description": (
                "Räume der HS Aalen mit Ausstattungsmerkmalen (Beamer, Video, 360°). "
                "Über `/{room_id}/schedule` den Belegungsplan eines Raums abrufen."
            ),
        },
        {
            "name": "lectures",
            "description": (
                "Einzelne Vorlesungen aus der Datenbank. Filterbar nach Raum, Studiengang und Zeitraum. "
                "Für die vollständige Timetable-Ansicht `GET /api/v1/timetable` verwenden."
            ),
        },
        {
            "name": "studiengaenge",
            "description": (
                "Alle Studiengänge aus dem STARplan-System. "
                "Über `/{id}/lectures` alle Vorlesungen eines Studiengangs abrufen."
            ),
        },
        {
            "name": "events",
            "description": (
                "Campus-Events anlegen, bearbeiten und löschen. "
                "`GET /upcoming` liefert Events der nächsten N Tage. "
                "Mit `public_only=true` für den Gäste-Modus (ohne Login) filtern."
            ),
        },
        {
            "name": "images",
            "description": (
                "360°-Panoramabilder für Räume hochladen, abrufen und löschen. "
                "Bilder werden unter `/app/data/images/360/{room_id}/` gespeichert."
            ),
        },
        # ── Import & Automatisierung ────────────────────────────────────
        {
            "name": "schedule",
            "description": (
                "Persönlichen Stundenplan per StarPlan-iCal-URL importieren (`POST /sync`). "
                "Parst die `.ics`-Datei und reichert Einträge mit Raum- und Gebäude-IDs aus der DB an."
            ),
        },
        {
            "name": "scheduler",
            "description": (
                "Scraper-Scheduler Steuerung. `GET /status` zeigt den letzten Job-Lauf aus der DB. "
                "`GET /logs` liefert die letzten N Läufe mit Statistiken. "
                "`POST /trigger` startet den Scraper manuell."
            ),
        },
        # ── System ──────────────────────────────────────────────────────
        {
            "name": "status",
            "description": "API-Info (`GET /`) und Health-Check (`GET /health`) mit DB-Verbindungsstatus.",
        },
    ],
)

# Add CORS middleware
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in cors_origins else cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(buildings.router)
app.include_router(events.router)
app.include_router(lectures.router)
app.include_router(rooms.router)
app.include_router(studiengaenge.router)
app.include_router(timetable.router)
app.include_router(streetview.router)
app.include_router(settings.router)
app.include_router(images.router)
app.include_router(schedule.router)
app.include_router(scheduler.router)


@app.get("/", tags=["status"], summary="API Info", response_description="Basisinformationen zur API")
async def root() -> dict[str, Any]:
    """Gibt grundlegende Informationen zur API zurück."""
    return {
        "message": "CampusNow API",
        "version": os.getenv("API_VERSION", "1.0.0"),
        "docs": "/docs",
        "status": "UP",
    }


@app.get(
    "/health",
    tags=["status"],
    summary="Health Check",
    response_description="Aktueller Gesundheitsstatus des Services und der Datenbankverbindung",
    responses={
        200: {
            "description": "Service ist erreichbar (kann dennoch `unhealthy` sein wenn DB nicht verbunden)",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "Alles OK",
                            "value": {"status": "healthy", "database": "connected"},
                        },
                        "unhealthy": {
                            "summary": "Datenbank nicht verbunden",
                            "value": {"status": "unhealthy", "database": "disconnected"},
                        },
                    }
                }
            },
        }
    },
)
async def health_check() -> dict[str, Any]:
    """Prüft ob der Service und die MongoDB-Verbindung erreichbar sind."""
    try:
        if mongo_client.connect():
            return {
                "status": "healthy",
                "database": "connected",
            }
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }
    except Exception as exc:
        logger.error(f"Health check error: {exc}")
        return {
            "status": "unhealthy",
            "error": str(exc),
        }


@app.on_event("startup")
async def startup_event() -> None:
    """Handle API startup event."""
    logger.info("=" * 60)
    logger.info("CampusNow - REST API Service Starting")
    logger.info("=" * 60)

    if mongo_client.connect():
        logger.info("✓ MongoDB connection established")
    else:
        logger.warning("⚠ MongoDB connection failed - retrying...")


@app.on_event("shutdown")
async def shutdown_event() -> None:
    """Handle API shutdown event."""
    logger.info("Shutting down API service...")
    mongo_client.disconnect()
    logger.info("✓ API service shut down")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
