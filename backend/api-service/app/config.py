"""Configuration settings for CampusNow API service."""

import os
from typing import ClassVar

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application configuration settings."""

    # MongoDB
    MONGO_URI: str = os.getenv(
        "MONGO_URI",
        "mongodb://admin:campusnow_secret_2025@mongodb:27017/campusnow",
    )
    MONGO_DB: str = os.getenv("MONGO_DB", "campusnow")

    # API
    API_TITLE: str = os.getenv("API_TITLE", "CampusNow API")
    API_VERSION: str = os.getenv("API_VERSION", "1.0.0")
    API_PORT: int = int(os.getenv("API_PORT", 8000))

    # CORS
    CORS_ORIGINS: ClassVar[list[str]] = [
        x.strip() for x in os.getenv("CORS_ORIGINS", "*").split(",")
    ]

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Scraper
    SCRAPER_SCHEDULE_HOUR: int = int(os.getenv("SCRAPER_SCHEDULE_HOUR", 6))
    SCRAPER_SCHEDULE_MINUTE: int = int(os.getenv("SCRAPER_SCHEDULE_MINUTE", 0))
    STARPLAN_BASE_URL: str = os.getenv(
        "STARPLAN_BASE_URL",
        "https://stundenplan.hs-aalen.de",
    )


settings = Settings()
