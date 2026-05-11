"""iCal parser for extracting lecture data from iCalendar files."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import icalendar
import requests

logger = logging.getLogger(__name__)

# Entfernt führende Titel ("Prof. Dr.", "Dipl.-Ing.", etc.)
_TITLE_STRIP_RE = re.compile(r'^(?:(?:Prof|Dr|Dipl)\.?\s+)+', re.IGNORECASE)
# Prüft ob ein einzelnes Wort wie ein Namens-Token aussieht:
# Startet mit Großbuchstabe, mindestens ein Kleinbuchstabe, kann Bindestriche enthalten
_NAME_WORD_RE = re.compile(r'^[A-ZÄÖÜ][a-zäöüß][a-zäöüßA-ZÄÖÜ\-]*$')


class IcalParser:
    """Parser for iCal files to extract lecture information."""

    @staticmethod
    def parse_ical_from_url(
        url: str,
        source_type: str = "room",
        source_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Lädt und parst eine iCal-Datei von einer URL."""
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
            logger.error(f"Error parsing iCal from {url}: {e}", exc_info=True)
            return []

    @staticmethod
    def _extract_event(
        component: Any,
        source_type: str = "room",
        source_id: str | None = None,
    ) -> dict[str, Any] | None:
        """Extrahiert Vorlesungsdaten aus einem iCal-VEVENT."""
        try:
            summary     = str(component.get("summary", ""))
            description = str(component.get("description", ""))
            raw_location = str(component.get("location", ""))
            start_time  = component.decoded("dtstart")
            end_time    = component.decoded("dtend")
            uid         = str(component.get("uid", ""))

            # Location: StarPlan hängt manchmal ", Canvas" oder andere Plattformen an –
            # nur der erste Teil (der echte Raum) ist relevant.
            location = raw_location.split(",")[0].strip()

            professor   = IcalParser._extract_professor(description)
            module_name = IcalParser._extract_module_name(summary)
            module_id   = IcalParser._extract_module_id(summary)

            duration = end_time - start_time if end_time and start_time else None
            duration_minutes = int(duration.total_seconds() / 60) if duration else 90

            return {
                "lecture_id":       uid or f"{location}_{start_time.isoformat()}",
                "module_name":      module_name,
                "module_id":        module_id,
                "room_number":      location,
                "professor":        professor,
                "start_time":       start_time,
                "end_time":         end_time,
                "day_of_week":      start_time.strftime("%A") if start_time else "Unknown",
                "duration_minutes": duration_minutes,
                "source_type":      source_type,
                "created_at":       datetime.now(),
            }

        except Exception as e:
            logger.warning(f"Error extracting event: {e}")
            return None

    @staticmethod
    def _extract_professor(description: str) -> str | None:
        """Extrahiert den Dozentennamen aus der Description.

        StarPlan-Description-Struktur (Zeilen getrennt durch \\n):
          1. Modulname (ggf. mit Modulnummer)
          2. Dozent (wenn vorhanden)
          3. Planungsgruppe (z. B. "IN S1")
          4. Optional: Canvas-URL o. ä.

        Kriterien für einen Dozenten-Namen:
        - Nach Titel-Stripping (Prof./Dr./Dipl.) verbleiben 1–4 Wörter
        - Jedes Wort startet mit Großbuchstabe und enthält mindestens einen Kleinbuchstaben
          (schließt Abkürzungen wie "MLD", "MIN", "ETI" aus)
        - Ohne Titel mind. 2 Wörter (sonst zu viele False Positives)
        """
        lines = [ln.strip() for ln in description.split("\n") if ln.strip()]
        for line in lines[1:]:
            if re.match(r'^[A-Z]{2,6}\s+S\d', line):  # Planungsgruppe → stop
                break
            if IcalParser._is_professor_name(line):
                return line
        return None

    @staticmethod
    def _is_professor_name(line: str) -> bool:
        """Gibt True zurück wenn die Zeile wie ein Personenname aussieht."""
        stripped = _TITLE_STRIP_RE.sub("", line).strip()
        had_title = stripped != line
        words = stripped.split()
        if not words or len(words) > 4:
            return False
        # Ohne Titel: mindestens 2 Wörter erforderlich
        if not had_title and len(words) < 2:
            return False
        return all(_NAME_WORD_RE.match(w) for w in words)

    @staticmethod
    def _extract_module_name(summary: str) -> str:
        """Extrahiert den sauberen Modulnamen ohne Modulnummer.

        Beispiel: "Rechnerarchitektur (31-57103)" → "Rechnerarchitektur"
        """
        name = re.sub(r"\s*\(\d[\d\-]*\)\s*", " ", summary).strip()
        return name or summary

    @staticmethod
    def _extract_module_id(summary: str) -> str | None:
        """Extrahiert die Modulnummer aus dem Summary.

        Beispiel: "Rechnerarchitektur (31-57103)" → "31-57103"
        """
        match = re.search(r"\((\d[\d\-]+)\)", summary)
        return match.group(1) if match else None

    @staticmethod
    def _extract_courses(description: str) -> list[str]:
        """Extrahiert Planungsgruppen-Kürzel aus der Description.

        Beispiele: "IN S1", "AI S2+3", "ETI S4"
        """
        pattern = r"\b([A-Z]{2,6}\s+S\d+(?:\+\d+)*)\b"
        return list(set(re.findall(pattern, description)))
