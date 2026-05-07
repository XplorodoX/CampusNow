"""Scraper for public events from the HS Aalen website."""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

MONTHS_DE: dict[str, int] = {
    "jan": 1, "januar": 1,
    "feb": 2, "februar": 2,
    "mär": 3, "märz": 3,
    "apr": 4, "april": 4,
    "mai": 5,
    "jun": 6, "juni": 6,
    "jul": 7, "juli": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9,
    "okt": 10, "oktober": 10,
    "nov": 11, "november": 11,
    "dez": 12, "dezember": 12,
}

# Matches "24. März 2026", "24. März", "4. Apr.", "4. Mai 2026"
_DATE_PATTERN = re.compile(
    r"(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\.?\s*(\d{4})?",
    re.UNICODE,
)

# Matches "13:00 bis 15:00 Uhr" or "18:00 Uhr"
_TIME_RANGE_PATTERN = re.compile(r"(\d{1,2}:\d{2})(?:\s+bis\s+(\d{1,2}:\d{2}))?\s+Uhr")


def _parse_german_date(text: str, fallback_year: int | None = None) -> datetime | None:
    """Parse a German date token like '24. März 2026' or '4. Apr.'."""
    m = _DATE_PATTERN.search(text.strip())
    if not m:
        return None
    day = int(m.group(1))
    month_key = m.group(2).lower()[:3]
    month = MONTHS_DE.get(month_key)
    if not month:
        return None
    year = int(m.group(3)) if m.group(3) else (fallback_year or datetime.now().year)
    try:
        return datetime(year, month, day)
    except ValueError:
        return None


def _parse_date_field(raw: str) -> tuple[datetime | None, datetime | None]:
    """
    Parse the event-card date string into (start_date, end_date).

    Handles:
      - "4. Mai 2026"                     → single date
      - "24. März bis 28. Juli 2026"      → cross-month range
      - "4. bis 7. Mai 2026"              → same-month range (start has no month)
      - "21. Apr. bis 13. Juni 2026"      → abbreviated month range
    """
    raw = raw.strip()

    # Split on " bis " (case-insensitive)
    parts = re.split(r"\s+bis\s+", raw, maxsplit=1, flags=re.IGNORECASE)

    if len(parts) == 1:
        # Single date
        start = _parse_german_date(parts[0])
        return start, None

    left, right = parts[0].strip(), parts[1].strip()

    end = _parse_german_date(right)

    # Try to parse start normally first
    start = _parse_german_date(left, fallback_year=end.year if end else None)

    # If start has no month (e.g. "4." only), borrow month from end
    if start is None and end is not None:
        day_match = re.match(r"^(\d{1,2})\.?\s*$", left)
        if day_match:
            try:
                start = datetime(end.year, end.month, int(day_match.group(1)))
            except ValueError:
                pass

    return start, end


def _parse_time_field(raw: str) -> tuple[str | None, str | None]:
    """Parse time string into (start_time, end_time) as 'HH:MM' strings."""
    m = _TIME_RANGE_PATTERN.search(raw)
    if not m:
        return None, None
    return m.group(1), m.group(2)


class HsAalenEventsScraper:
    """Scrape public events from https://www.hs-aalen.de/aktuelles/veranstaltungen/."""

    BASE_URL = "https://www.hs-aalen.de"
    EVENTS_URL = "https://www.hs-aalen.de/aktuelles/veranstaltungen/"
    MAX_PAGES = 20

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/123.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "de-DE,de;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def scrape_events(self) -> list[dict[str, Any]]:
        """Fetch all events across all pages. Returns a list of event dicts."""
        all_events: list[dict[str, Any]] = []

        for page in range(1, self.MAX_PAGES + 1):
            url = self._page_url(page)
            logger.info("Fetching events page %d: %s", page, url)

            try:
                response = self.session.get(url, timeout=20)
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.error("Failed to fetch page %d: %s", page, exc)
                break

            soup = BeautifulSoup(response.content, "html.parser")
            events = self._parse_page(soup)

            if not events:
                logger.info("No events on page %d — stopping", page)
                break

            all_events.extend(events)
            logger.info("Page %d: %d events found", page, len(events))

            if not self._has_next_page(soup):
                break

        logger.info("Total events scraped: %d", len(all_events))
        return all_events

    def _page_url(self, page: int) -> str:
        if page == 1:
            return self.EVENTS_URL
        # TYPO3 Solr pagination: ?tx_solr[page]=N
        params = urlencode({"tx_solr[page]": page})
        return f"{self.EVENTS_URL}?{params}"

    def _parse_page(self, soup: BeautifulSoup) -> list[dict[str, Any]]:
        """Extract all event-card elements from the page."""
        cards = soup.find_all("a", class_="event-card")
        events = []
        for card in cards:
            event = self._parse_card(card)
            if event:
                events.append(event)
        return events

    def _parse_card(self, card: Any) -> dict[str, Any] | None:
        href = card.get("href", "")
        detail_url = href if href.startswith("http") else f"{self.BASE_URL}{href}"

        # Title
        title_tag = card.find("h3", class_="headline") or card.find(re.compile(r"^h[1-6]$"))
        if not title_tag:
            return None
        title = title_tag.get_text(strip=True)
        if not title:
            return None

        # Date field: <div class="event-card-information-date">
        date_div = card.find("div", class_="event-card-information-date")
        raw_date = date_div.get_text(strip=True) if date_div else ""
        start_date, end_date = _parse_date_field(raw_date) if raw_date else (None, None)

        # Time field: <div class="event-card-information-time">
        time_div = card.find("div", class_="event-card-information-time")
        raw_time = time_div.get_text(strip=True) if time_div else ""
        start_time, end_time = _parse_time_field(raw_time) if raw_time else (None, None)

        # Derive a stable unique key from the detail URL slug
        slug = detail_url.rstrip("/").rsplit("/", 1)[-1]

        return {
            "slug": slug,
            "title": title,
            "detail_url": detail_url,
            "start_date": start_date,
            "end_date": end_date,
            "start_time": start_time,
            "end_time": end_time,
            "raw_date": raw_date,
            "raw_time": raw_time,
            "source": "hs-aalen-website",
            "scraped_at": datetime.now(),
        }

    def _has_next_page(self, soup: BeautifulSoup) -> bool:
        """Return True when a 'nächste' pagination link exists."""
        return bool(soup.find("a", class_="pagination__list__button__next"))

    def close(self) -> None:
        self.session.close()
