"""Configuration settings for CampusNow scraper service."""

import os

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

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Scraper
    SCRAPER_SCHEDULE_HOUR: int = int(os.getenv("SCRAPER_SCHEDULE_HOUR", 6))
    SCRAPER_SCHEDULE_MINUTE: int = int(os.getenv("SCRAPER_SCHEDULE_MINUTE", 0))
    STARPLAN_BASE_URL: str = os.getenv(
        "STARPLAN_BASE_URL",
        "https://stundenplan.hs-aalen.de",
    )

    # Image Storage
    IMAGE_STORE_DIR: str = "/app/data/images/360"


settings = Settings()
