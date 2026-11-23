"""
Greenhouse Job Board API adapter.

Fetches public job listings from Greenhouse board API and maps them to
the unified JobListing schema.  Handles rate-limiting (HTTP 429) with
exponential back-off, request timeouts, and transient errors.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.services.jobs.schemas import JobListing

logger = logging.getLogger(__name__)

_BASE_URL = "https://boards-api.greenhouse.io/v1/boards"
_TIMEOUT_SECONDS = 30.0
_MAX_RETRIES = 3
_INITIAL_BACKOFF = 1.0  # seconds


def _strip_html(html: str) -> str:
    """Convert an HTML string to clean plain text."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


def _detect_work_mode(text: str) -> Optional[str]:
    """Heuristically detect remote / hybrid / onsite from text."""
    lower = text.lower()
    if re.search(r"\bremote\b", lower):
        return "remote"
    if re.search(r"\bhybrid\b", lower):
        return "hybrid"
    if re.search(r"\bon[- ]?site\b", lower):
        return "onsite"
    return None


def _detect_experience_level(text: str) -> Optional[str]:
    """Heuristically detect seniority level from text."""
    lower = text.lower()
    if re.search(r"\bintern(ship)?\b", lower):
        return "intern"
    if re.search(r"\bjunior\b|entry[- ]?level", lower):
        return "junior"
    if re.search(r"\bmid[- ]?(level|senior)?\b", lower):
        return "mid"
    if re.search(r"\bsenior\b|\bsr\.?\b", lower):
        return "senior"
    if re.search(r"\bstaff\b", lower):
        return "staff"
    if re.search(r"\bprincipal\b", lower):
        return "principal"
    if re.search(r"\blead\b|\bmanager\b|\bdirector\b", lower):
        return "lead"
    return None


def _parse_job(raw: dict, board_token: str) -> JobListing:
    """Map a single Greenhouse API job object to a JobListing."""
    location_name = ""
    if raw.get("location"):
        location_name = raw["location"].get("name", "")

    description_html: str = raw.get("content", "") or ""
    description_text = _strip_html(description_html)

    title: str = raw.get("title", "")
    combined_text = f"{title} {location_name} {description_text}"

    posted_at: Optional[datetime] = None
    updated_at_raw = raw.get("updated_at") or raw.get("created_at")
    if updated_at_raw:
        try:
            posted_at = datetime.fromisoformat(
                updated_at_raw.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    absolute_url = raw.get("absolute_url", "")

    return JobListing(
        id=str(raw.get("id", "")),
        title=title,
        company=board_token,
        location=location_name,
        description=description_text,
        url=absolute_url,
        source="greenhouse",
        posted_at=posted_at,
        work_mode=_detect_work_mode(combined_text),
        experience_level=_detect_experience_level(combined_text),
        raw_data=raw,
    )


class GreenhouseAdapter:
    """Async adapter for the Greenhouse public job-board API."""

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
    # HTTP helper with retry / back-off
    # ------------------------------------------------------------------

    async def _request(self, url: str, params: dict | None = None) -> httpx.Response:
        """Execute a GET request with retry logic for 429 / 5xx."""
        client = await self._get_client()
        backoff = _INITIAL_BACKOFF

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await client.get(url, params=params)

                if response.status_code == 429:
                    retry_after = float(
                        response.headers.get("Retry-After", backoff)
                    )
                    logger.warning(
                        "Greenhouse 429 rate-limit hit (attempt %d/%d). "
                        "Retrying in %.1fs …",
                        attempt,
                        _MAX_RETRIES,
                        retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    backoff *= 2
                    continue

                if response.status_code >= 500:
                    logger.warning(
                        "Greenhouse server error %d (attempt %d/%d). "
                        "Retrying in %.1fs …",
                        response.status_code,
                        attempt,
                        _MAX_RETRIES,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue

                response.raise_for_status()
                return response

            except httpx.TimeoutException:
                logger.warning(
                    "Greenhouse request timed out (attempt %d/%d).",
                    attempt,
                    _MAX_RETRIES,
                )
                if attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2

            except httpx.HTTPStatusError:
                raise

            except httpx.HTTPError as exc:
                logger.warning(
                    "Greenhouse HTTP error (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2

        # Should never reach here, but satisfy the type checker.
        raise httpx.HTTPError("Max retries exceeded for Greenhouse request")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        board_token: str,
        query: str | None = None,
    ) -> list[JobListing]:
        """
        List all jobs on a Greenhouse board, optionally filtered by *query*.

        Parameters
        ----------
        board_token:
            The company's Greenhouse board token (e.g. ``"github"``).
        query:
            Optional keyword to filter jobs client-side after fetching.

        Returns
        -------
        list[JobListing]
        """
        url = f"{_BASE_URL}/{board_token}/jobs"
        params = {"content": "true"}

        try:
            response = await self._request(url, params=params)
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            logger.error(
                "Failed to fetch Greenhouse jobs for board '%s': %s",
                board_token,
                exc,
            )
            raise

        data = response.json()
        raw_jobs: list[dict] = data.get("jobs", [])

        jobs = [_parse_job(raw, board_token) for raw in raw_jobs]

        if query:
            query_lower = query.lower()
            jobs = [
                j
                for j in jobs
                if query_lower in j.title.lower()
                or query_lower in j.description.lower()
                or query_lower in j.location.lower()
            ]

        logger.info(
            "Greenhouse board '%s': fetched %d jobs (query=%r).",
            board_token,
            len(jobs),
            query,
        )
        return jobs

    async def get_job(
        self,
        board_token: str,
        job_id: int,
    ) -> JobListing:
        """
        Fetch a single job by ID from a Greenhouse board.

        Raises
        ------
        httpx.HTTPStatusError
            If the job is not found (404) or another HTTP error occurs.
        """
        url = f"{_BASE_URL}/{board_token}/jobs/{job_id}"
        params = {"content": "true"}

        response = await self._request(url, params=params)
        raw = response.json()
        return _parse_job(raw, board_token)
