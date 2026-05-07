"""iCal parser for extracting lecture data from iCalendar files."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import icalendar
import requests

logger = logging.getLogger(__name__)


class IcalParser:
    """Parser for iCal files to extract lecture information."""

    @staticmethod
    def parse_ical_from_url(
        url: str,
        source_type: str = "room",
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Load and parse iCal file from URL.

        Args:
            url: URL to the iCal file
            source_type: 'room' or 'course'
            source_id: Room-ID or Course-ID

        Returns:
            List of lecture dictionaries
        """
        try:
            logger.info(f"Fetching iCal from {url}...")
            response = requests.get(url, timeout=15)
            response.raise_for_status()

            ical_data = icalendar.Calendar.from_ical(response.content)
            lectures = []

            for component in ical_data.walk():
                if component.name == "VEVENT":
                    lecture = IcalParser._extract_event(component, source_type, source_id)
                    if lecture:
                        lectures.append(lecture)

            logger.info(f"Parsed {len(lectures)} lectures from {url}")
            return lectures

        except Exception as e:
            logger.error(
                f"Error parsing iCal from {url}: {e}",
                exc_info=True,
            )
            return []

    @staticmethod
    def _extract_event(
        component: Any,
        source_type: str = "room",
        source_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Extract lecture data from iCal event.

        Args:
            component: iCalendar event component
            source_type: 'room' or 'course'
            source_id: Room-ID or Course-ID

        Returns:
            Dictionary with lecture data or None on error
        """
        try:
            # Extract base information
            summary = str(component.get("summary", "N/A"))
            description = str(component.get("description", ""))
            location = str(component.get("location", ""))
            start_time = component.decoded("dtstart")
            end_time = component.decoded("dtend")
            uid = str(component.get("uid", ""))

            # Parse additional information from summary/description
            professor = IcalParser._extract_professor(summary, description)
            module_name = IcalParser._extract_module_name(summary)
            courses = IcalParser._extract_courses(description)

            # Calculate duration
            duration = end_time - start_time if end_time and start_time else None
            duration_minutes = duration.total_seconds() / 60 if duration else 90

            # Day of week
            day_of_week = start_time.strftime("%A") if start_time else "Unknown"

            event = {
                "lecture_id": uid or f"{location}_{start_time.isoformat()}",
                "summary": summary,
                "room_number": location,
                "professor": professor,
                "module_name": module_name,
                "courses": courses,  # List of course codes
                "description": description,
                "start_time": start_time,
                "end_time": end_time,
                "day_of_week": day_of_week,
                "duration_minutes": int(duration_minutes),
                "source_type": source_type,
                "source_id": source_id,
                "created_at": datetime.now(),
            }

            logger.debug(f"Extracted: {module_name} in {location} ({start_time})")
            return event

        except Exception as e:
            logger.warning(f"Error extracting event: {e}")
            return None

    @staticmethod
    def _extract_professor(summary: str, _description: str) -> str | None:
        """Extract professor name from summary/description.

        Args:
            summary: Event summary
            _description: Event description

        Returns:
            Professor name or None
        """
        patterns = [
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\(.*\)",
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, summary)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def _extract_module_name(summary: str) -> str:
        """Extract module name from summary.

        Args:
            summary: Event summary

        Returns:
            Module name without parentheses content
        """
        module = re.sub(r"\s*\([^)]*\)\s*", " ", summary)
        return module.strip()

    @staticmethod
    def _extract_courses(description: str) -> list[str]:
        """Extract course codes from description.

        Pattern: "IN S1", "AI S2+3", "ETI S4", etc.

        Args:
            description: Event description

        Returns:
            List of unique course codes
        """
        course_pattern = r"\b([A-Z]{2,3}\s+S\d+(?:\+\d+)?)\b"
        courses = re.findall(course_pattern, description)
        return list(set(courses))  # Unique courses
