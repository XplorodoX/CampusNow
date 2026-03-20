#!/usr/bin/env python3
"""Main entry point for CampusNow scraper service."""

import logging
import os
import time
from typing import NoReturn

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

from scheduler.tasks import ScraperTasks

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")),
    format=("%(asctime)s - %(name)s - %(levelname)s - %(message)s"),
)
logger = logging.getLogger(__name__)


def main() -> NoReturn:
    """Main entry point for scraper service.

    This function:
    1. Initializes the APScheduler
    2. Schedules daily scrape jobs
    3. Runs initial scrape on startup
    4. Keeps the service running indefinitely

    Raises:
        KeyboardInterrupt: When Ctrl+C is pressed
    """
    logger.info("=" * 60)
    logger.info("CampusNow - Scraper Service Starting")
    logger.info("=" * 60)

    # Create scheduler
    scheduler = BackgroundScheduler()

    # Get schedule config from environment
    schedule_hour = int(os.getenv("SCRAPER_SCHEDULE_HOUR", "6"))
    schedule_minute = int(os.getenv("SCRAPER_SCHEDULE_MINUTE", "0"))

    logger.info(f"Scheduler configured for: {schedule_hour:02d}:{schedule_minute:02d} every day")

    # Add job: Run scraper daily at specified time
    scheduler.add_job(
        ScraperTasks.full_scrape_job,
        trigger=CronTrigger(
            hour=schedule_hour,
            minute=schedule_minute,
        ),
        id="full_scrape_daily",
        name="Full Scrape Job (Daily)",
        replace_existing=True,
    )

    # Optional: Run once on startup for initial data
    logger.info("Running initial scrape on startup...")
    ScraperTasks.full_scrape_job()

    # Start scheduler
    scheduler.start()
    logger.info("✓ Scheduler started successfully")

    # Keep process running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        scheduler.shutdown()
        logger.info("✓ Scheduler shut down")


if __name__ == "__main__":
    main()
