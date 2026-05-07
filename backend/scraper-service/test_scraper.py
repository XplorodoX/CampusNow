#!/usr/bin/env python3
"""Manual live test for StarPlan scraper against HS Aalen endpoints."""

from __future__ import annotations

import logging
import sys
from typing import Any

from scraper.ical_parser import IcalParser
from scraper.starplan_scraper import StarplanScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _sample_test_entries(entries: list[dict[str, Any]], sample_size: int) -> list[dict[str, Any]]:
    """Return deterministic sample entries from beginning of list."""
    return entries[:sample_size]


def _validate_and_parse_samples(
    scraper: StarplanScraper,
    entries: list[dict[str, Any]],
    source_type: str,
    id_key: str,
    name_key: str,
    sample_size: int = 3,
) -> tuple[int, int]:
    """Validate and parse sample iCal links.

    Returns:
        Tuple(valid_count, parsed_count)
    """
    valid_count = 0
    parsed_count = 0

    for entry in _sample_test_entries(entries, sample_size):
        source_id = entry.get(id_key)
        source_name = entry.get(name_key)
        ical_url = entry.get("ical_url")

        logger.info("Testing %s %s (%s)", source_type, source_name, source_id)
        logger.info("iCal URL: %s", ical_url)

        if not ical_url:
            logger.warning("Missing iCal URL for %s", source_name)
            continue

        if scraper.validate_ical_url(ical_url):
            valid_count += 1
            lectures = IcalParser.parse_ical_from_url(
                ical_url,
                source_type=source_type,
                source_id=str(source_id) if source_id is not None else None,
            )
            if lectures:
                parsed_count += 1
                first = lectures[0]
                logger.info(
                    "Parsed %s lectures, first summary=%s",
                    len(lectures),
                    first.get("summary"),
                )
            else:
                logger.warning("Valid iCal but no lectures parsed for %s", source_name)
        else:
            logger.warning("iCal URL validation failed for %s", source_name)

    return valid_count, parsed_count


def test_scraper_live() -> bool:
    """Run a live integration-style test against HS Aalen StarPlan."""
    logger.info("=" * 70)
    logger.info("LIVE TEST: STARPLAN SCRAPER")
    logger.info("=" * 70)

    scraper = StarplanScraper()

    try:
        data = scraper.scrape_ical_links()
        if not data:
            logger.error("Scraper returned no data")
            return False

        rooms = data.get("raeume", [])
        courses = data.get("studiengaenge", [])

        logger.info("Found %s rooms", len(rooms))
        logger.info("Found %s courses/planning groups", len(courses))

        if not rooms:
            logger.error("No rooms found")
            return False
        if not courses:
            logger.error("No courses/planning groups found")
            return False

        logger.info("Testing sample room iCal links...")
        room_valid, room_parsed = _validate_and_parse_samples(
            scraper=scraper,
            entries=rooms,
            source_type="room",
            id_key="room_id",
            name_key="room_number",
            sample_size=3,
        )

        logger.info("Testing sample course iCal links...")
        course_valid, course_parsed = _validate_and_parse_samples(
            scraper=scraper,
            entries=courses,
            source_type="course",
            id_key="course_id",
            name_key="code",
            sample_size=3,
        )

        logger.info("Room samples valid/parsed: %s/%s", room_valid, room_parsed)
        logger.info("Course samples valid/parsed: %s/%s", course_valid, course_parsed)

        success = (
            room_valid >= 1
            and room_parsed >= 1
            and course_valid >= 1
            and course_parsed >= 1
        )
        if success:
            logger.info("✅ LIVE TEST PASSED")
        else:
            logger.error("❌ LIVE TEST FAILED: insufficient valid/parsed samples")

        return success

    except Exception as exc:
        logger.error("❌ Live test failed: %s", exc, exc_info=True)
        return False

    finally:
        scraper.close()


if __name__ == "__main__":
    ok = test_scraper_live()
    sys.exit(0 if ok else 1)
