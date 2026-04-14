"""StarPlan scraper for collecting iCal links and schedule metadata."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

from scraper.study_program_mapping import STUDY_PROGRAM_NAME_BY_CODE

logger = logging.getLogger(__name__)


class StarplanScraper:
    """Scrape room and planning-group iCal links from HS Aalen StarPlan."""

    def __init__(self, base_url: str = "https://vorlesungen.htw-aalen.de"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                )
            }
        )

        self.mobile_url = f"{self.base_url}/splan/mobile?lan=de&acc=true&act=tt"
        self.path = "/splan"
        self.lang = "de"
        self.json_base_url = f"{self.base_url}{self.path}/json"
        self.ical_base_url = f"{self.base_url}{self.path}/ical"
        self.puid: str | None = None
        self.location_id: str | None = None

    def scrape_ical_links(self) -> dict[str, Any] | None:
        """Scrape iCal links for rooms and planning groups."""
        logger.info("Starting StarPlan scraping...")
        try:
            self._discover_runtime_config()
            rooms = self._scrape_rooms()
            courses = self._scrape_courses()
            return {
                "raeume": rooms,
                "studiengaenge": courses,
                "scraped_at": datetime.now().isoformat(),
            }
        except Exception as exc:
            logger.error("Error scraping StarPlan: %s", exc, exc_info=True)
            return None

    def _discover_runtime_config(self) -> None:
        """Parse runtime state from HTML and resolve endpoint defaults."""
        response = self.session.get(f"{self.mobile_url}&sel=ro", timeout=20)
        response.raise_for_status()
        html = response.text

        path_match = re.search(r'var\s+path\s*=\s*"([^"]+)"', html)
        if path_match:
            self.path = path_match.group(1).strip()

        lan_match = re.search(r"state\.lan\s*=\s*(true|false)", html)
        if lan_match:
            self.lang = "de" if lan_match.group(1) == "true" else "en"

        self.json_base_url = f"{self.base_url}{self.path}/json"
        self.ical_base_url = f"{self.base_url}{self.path}/ical"
        self.puid = self._get_default_planning_unit_id()
        self.location_id = self._get_default_location_id()

        logger.info(
            "Discovered config path=%s lang=%s puid=%s loc=%s",
            self.path,
            self.lang,
            self.puid,
            self.location_id,
        )

    def _json_get(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"m": method}
        if params:
            query.update(params)

        response = self.session.get(self.json_base_url, params=query, timeout=20)
        response.raise_for_status()
        payload = response.json()
        return self._normalize_payload(payload)

    def _normalize_payload(self, payload: Any) -> list[dict[str, Any]]:
        if not isinstance(payload, list):
            return []

        result = payload
        while len(result) == 1 and isinstance(result[0], list):
            result = result[0]

        if not isinstance(result, list):
            return []

        if result and isinstance(result[0], dict) and "error" in result[0]:
            logger.warning("StarPlan endpoint error: %s", result[0]["error"])
            return []

        return [item for item in result if isinstance(item, dict)]

    def _get_default_planning_unit_id(self) -> str | None:
        planning_units = self._json_get("getpus")
        if not planning_units:
            return None

        default = next((u for u in planning_units if u.get("dateasdefault")), planning_units[0])
        puid = default.get("id")
        return str(puid) if puid is not None else None

    def _get_default_location_id(self) -> str | None:
        locations = self._json_get("getlocs")
        if not locations:
            return None

        loc_id = locations[0].get("id")
        return str(loc_id) if loc_id is not None else None

    def _scrape_rooms(self) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if self.location_id:
            params["loc"] = self.location_id

        rooms_payload = self._json_get("getros", params=params)
        if not rooms_payload:
            logger.warning("No rooms from JSON endpoint, using HTML fallback")
            return self._scrape_rooms_from_html_fallback()

        rooms: list[dict[str, Any]] = []
        for item in rooms_payload:
            room_id = item.get("id")
            if room_id is None:
                continue

            room_id_str = str(room_id)
            room_label = str(item.get("shortname") or item.get("name") or room_id_str)

            rooms.append(
                {
                    "room_id": room_id_str,
                    "room_number": room_label,
                    "room_name": str(item.get("name") or room_label),
                    "ical_url": self._construct_ical_url("room", room_id_str),
                    "type": "room",
                    "scraped_at": datetime.now().isoformat(),
                }
            )
        return rooms

    def _scrape_courses(self) -> list[dict[str, Any]]:
        org_groups = self._json_get("getogs")
        if not org_groups:
            logger.warning("No org groups from JSON endpoint, using HTML fallback")
            return self._scrape_courses_from_html_fallback()

        courses: list[dict[str, Any]] = []
        seen_pgids: set[str] = set()

        for og in org_groups:
            og_id = og.get("id")
            if og_id is None:
                continue

            planning_groups = self._json_get("getPgsExt", params={"og": og_id})
            for pg in planning_groups:
                pg_id = pg.get("id")
                if pg_id is None:
                    continue

                pgid = str(pg_id)
                if pgid in seen_pgids:
                    continue
                seen_pgids.add(pgid)

                shortname = str(pg.get("shortname") or pgid)
                name = str(pg.get("name") or shortname)
                program_code = str(og.get("shortname") or "").strip() or shortname.split(" ")[0]
                program_name = self._resolve_program_name(program_code, str(og.get("name") or ""))
                semester = self._extract_semester_label(shortname, name)

                courses.append(
                    {
                        "course_id": pgid,
                        "name": name,
                        "code": shortname,
                        "semester": semester,
                        "program_id": str(og_id),
                        "program_code": program_code,
                        "program_name": program_name,
                        "og_id": str(og_id),
                        "og_code": str(og.get("shortname") or ""),
                        "og_name": str(og.get("name") or ""),
                        "ical_url": self._construct_ical_url("pg", pgid),
                        "type": "course",
                        "scraped_at": datetime.now().isoformat(),
                    }
                )

        return courses

    @staticmethod
    def _extract_semester_label(group_code: str, group_name: str) -> str:
        """Extract a semester label from StarPlan planning-group metadata."""
        code_match = re.search(r"\bS[0-9][0-9+_/-]*\b", group_code)
        if code_match:
            return code_match.group(0)

        name_match = re.search(r"Sem\.?\s*([0-9][0-9+_/-]*)", group_name, flags=re.IGNORECASE)
        if name_match:
            return f"S{name_match.group(1)}"

        return ""

    @staticmethod
    def _normalize_program_code(program_code: str) -> str:
        """Normalize program code for robust dictionary lookups."""
        normalized = re.sub(r"\s+", " ", program_code.strip().upper())
        return normalized.replace("–", "-").replace("—", "-")

    def _resolve_program_name(self, program_code: str, starplan_name: str) -> str:
        """Resolve full program name from static mapping with StarPlan fallback."""
        normalized_code = self._normalize_program_code(program_code)
        mapped_name = STUDY_PROGRAM_NAME_BY_CODE.get(normalized_code)
        if mapped_name:
            return mapped_name
        return starplan_name

    def _scrape_rooms_from_html_fallback(self) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.mobile_url}&sel=ro", timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        selector = soup.find("select", {"name": "ro"}) or soup.find("select", {"id": "ttroom"})
        if not selector:
            return []

        rooms: list[dict[str, Any]] = []
        for option in selector.find_all("option"):
            room_id = option.get("value")
            room_name = option.get_text(strip=True)
            if not room_id or room_id in {"0", "-1"}:
                continue

            rooms.append(
                {
                    "room_id": str(room_id),
                    "room_number": room_name,
                    "ical_url": self._construct_ical_url("room", str(room_id)),
                    "type": "room",
                    "scraped_at": datetime.now().isoformat(),
                }
            )
        return rooms

    def _scrape_courses_from_html_fallback(self) -> list[dict[str, Any]]:
        response = self.session.get(f"{self.mobile_url}&sel=kurs", timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        selector = soup.find("select", {"name": "kurs"})
        if not selector:
            return []

        courses: list[dict[str, Any]] = []
        for option in selector.find_all("option"):
            course_id = option.get("value")
            course_name = option.get_text(strip=True)
            if not course_id or course_id in {"0", "-1"}:
                continue

            courses.append(
                {
                    "course_id": str(course_id),
                    "name": course_name,
                    "code": str(course_id),
                    "ical_url": self._construct_ical_url("legacy_kurs", str(course_id)),
                    "type": "course",
                    "scraped_at": datetime.now().isoformat(),
                }
            )
        return courses

    def _construct_ical_url(self, selection_type: str, selection_id: str) -> str:
        params: dict[str, str] = {"lan": self.lang}
        if self.puid:
            params["puid"] = self.puid

        if selection_type == "room":
            params["type"] = "room"
            params["roomid"] = selection_id
        elif selection_type == "pg":
            params["type"] = "pg"
            params["pgid"] = selection_id
        elif selection_type == "legacy_kurs":
            params["sel"] = "kurs"
            params["kurs"] = selection_id
        else:
            raise ValueError(f"Unknown selection_type: {selection_type}")

        return f"{self.ical_base_url}?{urlencode(params)}"

    def validate_ical_url(self, url: str) -> bool:
        """Validate whether URL returns a usable iCal payload."""
        try:
            response = self.session.head(url, timeout=8, allow_redirects=True)
            if response.status_code >= 400 or response.status_code == 405:
                response = self.session.get(url, timeout=12, allow_redirects=True)

            if response.status_code != 200:
                return False

            content_type = response.headers.get("content-type", "").lower()
            if "calendar" in content_type or "ics" in content_type:
                return True

            return "VCALENDAR" in response.text[:128].upper()
        except Exception as exc:
            logger.warning("Could not validate iCal URL %s: %s", url, exc)
            return False

    def close(self) -> None:
        """Close HTTP session."""
        self.session.close()
        logger.info("Scraper session closed")
