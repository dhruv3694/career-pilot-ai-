"""
SearXNG meta-search adapter.

Provides web search, job search, and career-event search via a
self-hosted SearXNG instance.  Respects ``settings.SEARXNG_ENABLED``
and degrades gracefully if the instance is unreachable.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime
from typing import Optional

import httpx

from app.core.config import settings
from app.services.jobs.schemas import CareerEvent, JobListing, SearchResult

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 15.0


def _parse_datetime(value: str | None) -> Optional[datetime]:
    """Best-effort ISO-8601 datetime parsing."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _deterministic_id(text: str) -> str:
    """Generate a short deterministic ID from a string."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class SearXNGAdapter:
    """Async adapter for a self-hosted SearXNG instance."""

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(_TIMEOUT_SECONDS),
                follow_redirects=True,
            )
        return self._client

    async def close(self) -> None:
        """Gracefully close the underlying HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _raw_search(
        self,
        query: str,
        categories: list[str] | None = None,
        num_results: int = 10,
    ) -> list[dict]:
        """
        Execute a raw search against SearXNG and return the results list.

        Returns an empty list on any error (network, timeout, disabled).
        """
        if not settings.SEARXNG_ENABLED:
            logger.debug("SearXNG is disabled; skipping search.")
            return []

        base_url = str(settings.SEARXNG_URL).rstrip("/")
        url = f"{base_url}/search"

        params: dict[str, str | int] = {
            "q": query,
            "format": "json",
            "pageno": 1,
        }
        if categories:
            params["categories"] = ",".join(categories)

        try:
            client = await self._get_client()
            response = await client.get(url, params=params)
            response.raise_for_status()
        except httpx.ConnectError:
            logger.warning(
                "SearXNG instance at %s is unreachable (connection refused).",
                base_url,
            )
            return []
        except httpx.TimeoutException:
            logger.warning("SearXNG request timed out (%s).", base_url)
            return []
        except httpx.HTTPError as exc:
            logger.error("SearXNG request failed: %s", exc)
            return []

        data = response.json()
        results: list[dict] = data.get("results", [])
        return results[:num_results]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        categories: list[str] | None = None,
        num_results: int = 10,
    ) -> list[SearchResult]:
        """
        Perform a generic web search via SearXNG.

        Parameters
        ----------
        query:
            Free-text search query.
        categories:
            Optional SearXNG category filters (e.g. ``["general"]``).
        num_results:
            Maximum number of results to return.

        Returns
        -------
        list[SearchResult]
        """
        raw_results = await self._raw_search(query, categories, num_results)
        results: list[SearchResult] = []
        for item in raw_results:
            results.append(
                SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source=item.get("engine", ""),
                    published_at=_parse_datetime(
                        item.get("publishedDate") or item.get("published_date")
                    ),
                )
            )
        logger.info(
            "SearXNG search for %r returned %d results.", query, len(results)
        )
        return results

    async def search_jobs(
        self,
        query: str,
        location: str | None = None,
    ) -> list[JobListing]:
        """
        Search for job listings via SearXNG web search.

        Constructs a job-oriented query and maps web results into
        JobListing objects with best-effort field population.

        Parameters
        ----------
        query:
            Job-related search terms.
        location:
            Optional location to include in the query.

        Returns
        -------
        list[JobListing]
        """
        parts = [query, "jobs", "hiring"]
        if location:
            parts.append(location)
        full_query = " ".join(parts)

        raw_results = await self._raw_search(full_query, categories=["general"], num_results=20)

        jobs: list[JobListing] = []
        for item in raw_results:
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("content", "")

            # Infer company from the engine or URL domain.
            engine = item.get("engine", "")
            parsed_source = item.get("parsed_url", [])
            domain = parsed_source[1] if len(parsed_source) > 1 else engine

            jobs.append(
                JobListing(
                    id=_deterministic_id(url or title),
                    title=title,
                    company=domain,
                    location=location or "",
                    description=snippet,
                    url=url,
                    source=f"searxng:{engine}" if engine else "searxng",
                    posted_at=_parse_datetime(
                        item.get("publishedDate") or item.get("published_date")
                    ),
                )
            )

        logger.info(
            "SearXNG job search for %r returned %d results.",
            full_query,
            len(jobs),
        )
        return jobs

    async def search_events(
        self,
        query: str,
    ) -> list[CareerEvent]:
        """
        Search for career events (conferences, meetups, etc.) via SearXNG.

        Parameters
        ----------
        query:
            Event-related search terms.

        Returns
        -------
        list[CareerEvent]
        """
        full_query = f"{query} career event conference meetup"
        raw_results = await self._raw_search(
            full_query, categories=["general"], num_results=15
        )

        _EVENT_KEYWORDS = {
            "conference": "conference",
            "meetup": "meetup",
            "workshop": "workshop",
            "webinar": "webinar",
            "career fair": "career_fair",
            "hackathon": "meetup",
            "summit": "conference",
            "seminar": "workshop",
        }

        events: list[CareerEvent] = []
        for item in raw_results:
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("content", "")
            engine = item.get("engine", "")

            # Detect event type from title + snippet.
            event_type = ""
            combined_lower = f"{title} {snippet}".lower()
            for keyword, etype in _EVENT_KEYWORDS.items():
                if keyword in combined_lower:
                    event_type = etype
                    break

            published_at = _parse_datetime(
                item.get("publishedDate") or item.get("published_date")
            )

            events.append(
                CareerEvent(
                    id=_deterministic_id(url or title),
                    title=title,
                    description=snippet,
                    url=url,
                    source=f"searxng:{engine}" if engine else "searxng",
                    event_type=event_type,
                    start_date=published_at,  # best-effort approximation
                    is_verified=False,
                )
            )

        logger.info(
            "SearXNG event search for %r returned %d results.",
            query,
            len(events),
        )
        return events
