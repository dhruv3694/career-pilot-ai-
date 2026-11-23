"""
Career event discovery service.

Discovers career-related events (conferences, meetups, workshops, webinars,
career fairs) by searching the web via the SearXNG adapter when available,
with a direct httpx+BeautifulSoup fallback.
"""

from __future__ import annotations

import hashlib
import logging
import re
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES = frozenset(
    {"conference", "meetup", "workshop", "webinar", "career_fair", ""}
)


class CareerEvent(BaseModel):
    """A single career-related event."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str
    description: str = ""
    url: str = ""
    location: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: str = ""  # conference, meetup, workshop, webinar, career_fair
    source: str = ""
    is_verified: bool = False


class EventSearchResponse(BaseModel):
    """Aggregated response from an event discovery query."""

    events: list[CareerEvent] = Field(default_factory=list)
    total_results: int = 0
    search_query: str = ""
    search_location: Optional[str] = None
    search_time_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DATE_PATTERNS: list[tuple[str, str]] = [
    # ISO 8601
    (r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", "%Y-%m-%dT%H:%M"),
    (r"\d{4}-\d{2}-\d{2}", "%Y-%m-%d"),
    # US style
    (r"\d{1,2}/\d{1,2}/\d{4}", "%m/%d/%Y"),
    # Long form
    (r"\w+ \d{1,2},? \d{4}", None),  # handled manually
]


def _try_parse_date(text: str) -> Optional[datetime]:
    """Best-effort date extraction from a text fragment."""
    if not text:
        return None
    text = text.strip()

    # Try common formats
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%B %d %Y",
        "%b %d, %Y",
        "%b %d %Y",
        "%d %B %Y",
        "%d %b %Y",
    ):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Regex fallback – look for dates embedded in longer strings
    iso_match = re.search(r"(\d{4}-\d{2}-\d{2})", text)
    if iso_match:
        try:
            return datetime.strptime(iso_match.group(1), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            pass

    return None


def _classify_event_type(text: str) -> str:
    """Heuristic classification of event type from title/description."""
    lower = text.lower()
    if any(kw in lower for kw in ("conference", "conf", "summit")):
        return "conference"
    if any(kw in lower for kw in ("meetup", "meet-up", "meet up", "networking")):
        return "meetup"
    if any(kw in lower for kw in ("workshop", "bootcamp", "boot camp", "hands-on")):
        return "workshop"
    if any(kw in lower for kw in ("webinar", "online event", "virtual event", "livestream")):
        return "webinar"
    if any(kw in lower for kw in ("career fair", "job fair", "hiring event", "recruitment")):
        return "career_fair"
    return ""


def _content_hash(event: CareerEvent) -> str:
    """Deterministic hash for deduplication."""
    key = f"{event.title.lower().strip()}|{event.url.lower().strip()}"
    return hashlib.md5(key.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EventDiscoveryService:
    """Discover career-relevant events from the web."""

    def __init__(self) -> None:
        self._searxng_adapter: Any | None = None
        self._load_searxng()

    def _load_searxng(self) -> None:
        """Try to import the shared SearXNG adapter."""
        try:
            from app.services.jobs.searxng import SearxngAdapter  # type: ignore[import-untyped]

            self._searxng_adapter = SearxngAdapter()
            logger.info("SearXNG adapter loaded for event discovery.")
        except Exception:
            logger.info(
                "SearXNG adapter not available; will use direct web search fallback."
            )
            self._searxng_adapter = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def discover(
        self,
        query: str,
        location: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        event_types: list[str] | None = None,
        limit: int = 20,
    ) -> EventSearchResponse:
        """Search for career events matching the given criteria.

        Parameters
        ----------
        query:
            Free-text search query (e.g. "Python conference").
        location:
            Optional geographic filter (e.g. "San Francisco").
        date_from / date_to:
            Optional date window.
        event_types:
            Optional list of event type filters.
        limit:
            Maximum events to return.
        """
        start = time.perf_counter()
        errors: list[str] = []
        events: list[CareerEvent] = []

        # Build enriched search query
        search_query = self._build_search_query(query, location)

        # Search via SearXNG or direct web
        try:
            raw_events = await self._search_web_events(search_query, location)
            events.extend(raw_events)
        except Exception as exc:
            logger.exception("Web event search failed")
            errors.append(f"Web search error: {exc}")

        # Post-processing pipeline
        events = self._deduplicate(events)
        events = self._validate_dates(events)

        # Apply filters
        if event_types:
            allowed = {t.lower().strip() for t in event_types}
            events = [e for e in events if e.event_type in allowed]

        if date_from:
            events = [
                e
                for e in events
                if e.start_date is None or e.start_date >= date_from
            ]

        if date_to:
            events = [
                e for e in events if e.start_date is None or e.start_date <= date_to
            ]

        # Sort: verified first, then by start_date (events without dates last)
        events.sort(
            key=lambda e: (
                not e.is_verified,
                e.start_date or datetime.max.replace(tzinfo=timezone.utc),
            )
        )

        events = events[:limit]
        elapsed = (time.perf_counter() - start) * 1000

        return EventSearchResponse(
            events=events,
            total_results=len(events),
            search_query=search_query,
            search_location=location,
            search_time_ms=round(elapsed, 2),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Internal – search
    # ------------------------------------------------------------------

    @staticmethod
    def _build_search_query(query: str, location: str | None) -> str:
        """Enrich query with career-event keywords."""
        parts = [query.strip()]
        # Append event-related terms if not already present
        lower = query.lower()
        if not any(kw in lower for kw in ("event", "conference", "meetup", "workshop", "webinar", "career fair")):
            parts.append("event")
        if location:
            parts.append(location)
        return " ".join(parts)

    async def _search_web_events(
        self, query: str, location: str | None = None
    ) -> list[CareerEvent]:
        """Run the web search and return parsed CareerEvent objects."""
        # Try SearXNG first
        if self._searxng_adapter is not None:
            return await self._search_via_searxng(query, location)

        # Fallback: direct search via httpx
        return await self._search_direct(query)

    async def _search_via_searxng(
        self, query: str, location: str | None = None
    ) -> list[CareerEvent]:
        """Search using the SearXNG adapter."""
        events: list[CareerEvent] = []
        try:
            results = await self._searxng_adapter.search(query=query, categories="general", limit=30)
            for r in results:
                title = r.get("title", "")
                url = r.get("url", "")
                snippet = r.get("content", "") or r.get("snippet", "")
                source = r.get("engine", "searxng")

                event_type = _classify_event_type(f"{title} {snippet}")
                start_date = _try_parse_date(r.get("publishedDate", ""))

                # Check for well-known event platforms → mark verified
                is_verified = any(
                    domain in url.lower()
                    for domain in (
                        "eventbrite.com",
                        "meetup.com",
                        "lu.ma",
                        "hopin.com",
                        "conf.",
                        "conference.",
                    )
                )

                events.append(
                    CareerEvent(
                        title=title,
                        description=snippet[:500],
                        url=url,
                        location=location or "",
                        start_date=start_date,
                        event_type=event_type,
                        source=source,
                        is_verified=is_verified,
                    )
                )
        except Exception as exc:
            logger.warning("SearXNG search failed, falling back: %s", exc)
            events = await self._search_direct(query)

        return events

    async def _search_direct(self, query: str) -> list[CareerEvent]:
        """Fallback: search the web directly with httpx."""
        events: list[CareerEvent] = []
        search_url = "https://html.duckduckgo.com/html/"

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            ) as client:
                resp = await client.post(search_url, data={"q": query})
                resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")
            result_links = soup.select("a.result__a")

            for link in result_links[:30]:
                title = link.get_text(strip=True)
                href = link.get("href", "")
                # DuckDuckGo wraps URLs
                url_match = re.search(r"uddg=([^&]+)", href)
                if url_match:
                    from urllib.parse import unquote
                    href = unquote(url_match.group(1))

                snippet_el = link.find_next("a", class_="result__snippet")
                snippet = snippet_el.get_text(strip=True) if snippet_el else ""

                event_type = _classify_event_type(f"{title} {snippet}")

                is_verified = any(
                    domain in href.lower()
                    for domain in (
                        "eventbrite.com",
                        "meetup.com",
                        "lu.ma",
                        "hopin.com",
                    )
                )

                events.append(
                    CareerEvent(
                        title=title,
                        description=snippet[:500],
                        url=href,
                        event_type=event_type,
                        source="web_search",
                        is_verified=is_verified,
                    )
                )

        except Exception as exc:
            logger.warning("Direct web search failed: %s", exc)

        return events

    # ------------------------------------------------------------------
    # Post-processing
    # ------------------------------------------------------------------

    def _deduplicate(self, events: list[CareerEvent]) -> list[CareerEvent]:
        """Remove duplicate events based on title+URL hash."""
        seen: set[str] = set()
        unique: list[CareerEvent] = []
        for event in events:
            h = _content_hash(event)
            if h not in seen:
                seen.add(h)
                unique.append(event)
        return unique

    def _validate_dates(self, events: list[CareerEvent]) -> list[CareerEvent]:
        """Ensure dates are sane; drop obviously wrong ones."""
        validated: list[CareerEvent] = []
        now = datetime.now(tz=timezone.utc)
        far_future = now.replace(year=now.year + 5)

        for event in events:
            # Fix end before start
            if event.start_date and event.end_date and event.end_date < event.start_date:
                event.end_date = None

            # Drop dates too far in the future (likely parsing errors)
            if event.start_date and event.start_date > far_future:
                event.start_date = None
                event.end_date = None

            # Drop dates too far in the past (> 1 year ago)
            if event.start_date and event.start_date.year < now.year - 1:
                event.start_date = None
                event.end_date = None

            validated.append(event)

        return validated
