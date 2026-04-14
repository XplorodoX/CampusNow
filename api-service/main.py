#!/usr/bin/env python3
"""Main entry point for CampusNow REST API service."""

import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.mongo_client import mongo_client
from app.routers import images, lectures, rooms, scheduler, studiengaenge

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

Stundenplan- und Raumverwaltungs-API für die **Hochschule Aalen**.

### Funktionen

- **Vorlesungen** – Stundenplan-Daten filtern nach Raum, Studiengang und Datum
- **Räume** – Raumdaten inkl. Ausstattung und Belegungspläne
- **Studiengänge** – Alle Studiengänge und ihre Vorlesungen
- **360°-Bilder** – Panorama-Bilder von Räumen verwalten und abrufen
- **Scheduler** – Status und manuelle Auslösung des Scrapers

### Datenquelle

Die Daten werden automatisch täglich um **06:00 Uhr** aus dem STARplan-System der HS Aalen gescrapt.
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
        {
            "name": "lectures",
            "description": "Vorlesungspläne abrufen und verwalten.",
        },
        {
            "name": "rooms",
            "description": "Räume und Raumbelegungen der HS Aalen.",
        },
        {
            "name": "studiengaenge",
            "description": "Studiengänge und ihre zugehörigen Vorlesungen.",
        },
        {
            "name": "images",
            "description": "360°-Panoramabilder für Räume hochladen und abrufen.",
        },
        {
            "name": "scheduler",
            "description": "Scraper-Scheduler Status und manuelle Steuerung.",
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
app.include_router(lectures.router)
app.include_router(rooms.router)
app.include_router(studiengaenge.router)
app.include_router(images.router)
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
