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
    description="Microservice für Stundenplan-Management der HS Aalen",
    version=os.getenv("API_VERSION", "1.0.0"),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
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


@app.get("/")
async def root() -> dict[str, Any]:
    """Root endpoint returning API information."""
    return {
        "message": "CampusNow API",
        "version": os.getenv("API_VERSION", "1.0.0"),
        "docs": "/docs",
        "status": "UP",
    }


@app.get("/health")
async def health_check() -> dict[str, Any]:
    """Health check endpoint."""
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
