"""Unit tests for iCal import helpers and service logic."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from icalendar import Event

from app.services import ical_import


def test_validate_ical_url_accepts_allowed_host() -> None:
    ical_import._validate_ical_url("https://vorlesungen.htw-aalen.de/splan/ical?pgid=1")


@pytest.mark.parametrize(
    ("url", "error_substring"),
    [
        ("ftp://vorlesungen.htw-aalen.de/test.ics", "HTTP/HTTPS"),
        ("https://localhost/test.ics", "Interne Adressen"),
        ("https://127.0.0.1/test.ics", "Interne Adressen"),
        ("https://example.com/test.ics", "nicht erlaubt"),
        ("https:///test.ics", "Kein Hostname"),
    ],
)
def test_validate_ical_url_rejects_invalid_hosts(url: str, error_substring: str) -> None:
    with pytest.raises(ValueError, match=error_substring):
        ical_import._validate_ical_url(url)


def test_fetch_and_parse_returns_only_vevents(monkeypatch: pytest.MonkeyPatch) -> None:
    ics = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-1
SUMMARY:Algorithmen (Prof. Müller)
LOCATION:Z106
DESCRIPTION:Vorlesung
DTSTART:20260423T080000Z
DTEND:20260423T093000Z
END:VEVENT
BEGIN:VTODO
SUMMARY:Ignored
END:VTODO
END:VCALENDAR
""".encode("utf-8")

    response = MagicMock()
    response.content = ics
    response.raise_for_status = MagicMock()

    monkeypatch.setattr(ical_import.requests, "get", lambda *args, **kwargs: response)

    entries = ical_import.fetch_and_parse("https://vorlesungen.htw-aalen.de/splan/ical?pgid=1")

    assert len(entries) == 1
    assert entries[0]["uid"] == "test-1"
    assert entries[0]["room_number"] == "Z106"
    response.raise_for_status.assert_called_once()


def test_parse_vevent_returns_none_on_invalid_payload() -> None:
    component = MagicMock()
    component.get.side_effect = Exception("broken")

    assert ical_import._parse_vevent(component) is None


def test_parse_vevent_extracts_expected_fields() -> None:
    event = Event()
    event.add("uid", "evt-42")
    event.add("summary", "Algorithmen und Datenstrukturen (Prof. Mueller)")
    event.add("location", " Z106 ")
    event.add("description", "Pflichtveranstaltung")
    event.add("dtstart", datetime(2026, 4, 23, 8, 0, tzinfo=timezone.utc))
    event.add("dtend", datetime(2026, 4, 23, 9, 30, tzinfo=timezone.utc))

    parsed = ical_import._parse_vevent(event)

    assert parsed is not None
    assert parsed["uid"] == "evt-42"
    assert parsed["module_name"] == "Algorithmen und Datenstrukturen"
    assert parsed["room_number"] == "Z106"
    assert parsed["duration_minutes"] == 90
    assert parsed["day_of_week"] == "Thursday"


def test_enrich_with_db_adds_room_and_building_ids() -> None:
    entries = [
        {"uid": "1", "room_number": "Z106", "summary": "A", "module_name": "A"},
        {"uid": "2", "room_number": "UNKNOWN", "summary": "B", "module_name": "B"},
        {"uid": "3", "room_number": None, "summary": "C", "module_name": "C"},
    ]

    db = MagicMock()
    db.rooms.find.return_value = [{"room_number": "Z106", "room_id": "Z106", "building_id": "Z"}]

    enriched = ical_import.enrich_with_db(entries, db)

    assert len(enriched) == 3
    assert enriched[0]["room_known"] is True
    assert enriched[0]["room_id"] == "Z106"
    assert enriched[0]["building_id"] == "Z"
    assert enriched[1]["room_known"] is False
    assert enriched[1]["room_id"] is None
    assert enriched[2]["room_known"] is False
    assert all("imported_at" in item for item in enriched)
    db.rooms.find.assert_called_once()


def test_clean_module_name_and_extract_professor_helpers() -> None:
    summary = "Algorithmen und Datenstrukturen (Prof. Mueller)"

    assert ical_import._clean_module_name(summary) == "Algorithmen und Datenstrukturen"
    assert ical_import._extract_professor("Einführung Max Mustermann") == "Max Mustermann"
    assert ical_import._extract_professor("Ohne Name") is None
