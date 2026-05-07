"""iCal import service – parst eine StarPlan-URL und reichert die Daten mit DB-Infos an."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import icalendar
import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 15

# Erlaubte Hosts für iCal-URLs (SSRF-Schutz)
_ALLOWED_HOSTS = {
    "vorlesungen.htw-aalen.de",
    "stundenplan.hs-aalen.de",
    "www.hs-aalen.de",
}


def _validate_ical_url(url: str) -> None:
    """Prüft ob die iCal-URL erlaubt ist (verhindert SSRF-Angriffe)."""
    try:
        parsed = urlparse(url)
    except Exception:
        raise ValueError("Ungültige URL")

    if parsed.scheme not in ("http", "https"):
        raise ValueError("Nur HTTP/HTTPS erlaubt")

    host = (parsed.hostname or "").lower()
    if not host:
        raise ValueError("Kein Hostname in der URL")

    # Interne/lokale Adressen blockieren
    blocked_prefixes = ("localhost", "127.", "10.", "192.168.", "172.16.", "169.254.")
    if any(host == b or host.startswith(b) for b in blocked_prefixes):
        raise ValueError("Interne Adressen sind nicht erlaubt")

    if host not in _ALLOWED_HOSTS:
        raise ValueError(
            f"Host '{host}' ist nicht erlaubt. Erlaubte Hosts: {', '.join(sorted(_ALLOWED_HOSTS))}"
        )


def fetch_and_parse(url: str) -> list[dict[str, Any]]:
    """Lädt eine iCal-URL herunter und gibt eine Liste geparster Vorlesungen zurück."""
    _validate_ical_url(url)
    response = requests.get(url, timeout=_TIMEOUT, headers={"User-Agent": "CampusNow/1.0"})
    response.raise_for_status()
    cal = icalendar.Calendar.from_ical(response.content)

    entries: list[dict[str, Any]] = []
    for component in cal.walk():
        if component.name != "VEVENT":
            continue
        entry = _parse_vevent(component)
        if entry:
            entries.append(entry)

    return entries


def _parse_vevent(component: Any) -> dict[str, Any] | None:
    try:
        summary = str(component.get("summary", ""))
        location = str(component.get("location", ""))
        description = str(component.get("description", ""))
        uid = str(component.get("uid", ""))
        start = component.decoded("dtstart")
        end = component.decoded("dtend")

        duration_minutes = int((end - start).total_seconds() / 60) if start and end else 90

        return {
            "uid": uid,
            "module_name": _clean_module_name(summary),
            "summary": summary,
            "professor": _extract_professor(summary),
            "room_number": location.strip(),
            "start_time": start.isoformat() if start else None,
            "end_time": end.isoformat() if end else None,
            "day_of_week": start.strftime("%A") if start else None,
            "duration_minutes": duration_minutes,
            "description": description,
        }
    except Exception as exc:
        logger.warning("Skipping VEVENT: %s", exc)
        return None


def enrich_with_db(entries: list[dict[str, Any]], db: Any) -> list[dict[str, Any]]:
    """Ergänzt jeden Eintrag mit room_id und building_id aus der Datenbank."""
    # Alle Raumnummern auf einmal laden (vermeidet N+1-Queries)
    room_numbers = {e["room_number"] for e in entries if e.get("room_number")}
    rooms_by_number: dict[str, dict] = {
        r["room_number"]: r
        for r in db.rooms.find({"room_number": {"$in": list(room_numbers)}})
        if "room_number" in r
    }

    now = datetime.now().isoformat()
    enriched: list[dict[str, Any]] = []
    for entry in entries:
        room = rooms_by_number.get(entry.get("room_number", ""))
        enriched.append({
            **entry,
            "room_id": room.get("room_id") if room else None,
            "building_id": room.get("building_id") if room else None,
            # Gibt an ob der Raum in der DB bekannt ist
            "room_known": room is not None,
            "imported_at": now,
        })
    return enriched


def _clean_module_name(summary: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", summary).strip()


def _extract_professor(summary: str) -> str | None:
    match = re.search(r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)+)", summary)
    return match.group(1) if match else None
