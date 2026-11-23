"""
Lever Postings API adapter.

Fetches public job postings from the Lever postings API and maps them
to the unified JobListing schema.  Handles rate-limiting (HTTP 429)
with exponential back-off, request timeouts, and transient errors.
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.services.jobs.schemas import JobListing

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.lever.co/v0/postings"
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


def _build_description(lists_block: list[dict]) -> str:
    """
    Build a plain-text description from Lever's ``lists`` structure.

    Each element contains ``text`` (header) and ``content`` (HTML).
    """
    parts: list[str] = []
    for section in lists_block:
        header = section.get("text", "")
        content_html = section.get("content", "")
        body = _strip_html(content_html)
        if header:
            parts.append(header)
        if body:
            parts.append(body)
    return "\n\n".join(parts)


def _parse_posting(raw: dict, company: str) -> JobListing:
    """Map a single Lever posting object to a JobListing."""
    # Description can live in ``descriptionPlain``, ``description``, or
    # the structured ``lists`` array.
    description = raw.get("descriptionPlain", "") or ""
    if not description:
        description = _strip_html(raw.get("description", "") or "")
    lists_block = raw.get("lists", [])
    if lists_block:
        extra = _build_description(lists_block)
        if extra:
            description = f"{description}\n\n{extra}" if description else extra

    # Opening text (sometimes contains additional context)
    additional = raw.get("additionalPlain", "") or ""
    if not additional:
        additional = _strip_html(raw.get("additional", "") or "")
    if additional:
        description = f"{description}\n\n{additional}" if description else additional

    title: str = raw.get("text", "")
    location_name: str = ""
    categories = raw.get("categories", {})
    if categories:
        location_name = categories.get("location", "")
    if not location_name:
        location_name = raw.get("workplaceType", "")

    combined_text = f"{title} {location_name} {description}"

    # Lever timestamps are in milliseconds since epoch.
    posted_at: Optional[datetime] = None
    created_at_ms = raw.get("createdAt")
    if created_at_ms and isinstance(created_at_ms, (int, float)):
        try:
            posted_at = datetime.fromtimestamp(
                created_at_ms / 1000, tz=timezone.utc
            )
        except (ValueError, OSError):
            pass

    salary_range: Optional[str] = None
    salary_info = categories.get("salaryRange") if categories else None
    if salary_info:
        salary_range = str(salary_info)

    return JobListing(
        id=str(raw.get("id", "")),
        title=title,
        company=company,
        location=location_name,
        description=description.strip(),
        url=raw.get("hostedUrl", "") or raw.get("applyUrl", ""),
        source="lever",
        posted_at=posted_at,
        salary_range=salary_range,
        work_mode=_detect_work_mode(combined_text),
        experience_level=_detect_experience_level(combined_text),
        raw_data=raw,
    )


class LeverAdapter:
    """Async adapter for the Lever public postings API."""

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
                        "Lever 429 rate-limit hit (attempt %d/%d). "
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
                        "Lever server error %d (attempt %d/%d). "
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
                    "Lever request timed out (attempt %d/%d).",
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
                    "Lever HTTP error (attempt %d/%d): %s",
                    attempt,
                    _MAX_RETRIES,
                    exc,
                )
                if attempt == _MAX_RETRIES:
                    raise
                await asyncio.sleep(backoff)
                backoff *= 2

        raise httpx.HTTPError("Max retries exceeded for Lever request")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def search(
        self,
        company: str,
        query: str | None = None,
    ) -> list[JobListing]:
        """
        List all public postings for a Lever company, optionally filtered.

        Parameters
        ----------
        company:
            The company slug on Lever (e.g. ``"netflix"``).
        query:
            Optional keyword to filter postings client-side.

        Returns
        -------
        list[JobListing]
        """
        url = f"{_BASE_URL}/{company}"
        params: dict[str, str] = {"mode": "json"}

        try:
            response = await self._request(url, params=params)
        except (httpx.HTTPError, httpx.HTTPStatusError) as exc:
            logger.error(
                "Failed to fetch Lever postings for '%s': %s",
                company,
                exc,
            )
            raise

        raw_postings: list[dict] = response.json()
        if not isinstance(raw_postings, list):
            logger.error(
                "Unexpected Lever response type for '%s': %s",
                company,
                type(raw_postings).__name__,
            )
            raise ValueError(f"Unexpected Lever response type for {company}")

        jobs = [_parse_posting(raw, company) for raw in raw_postings]

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
            "Lever company '%s': fetched %d postings (query=%r).",
            company,
            len(jobs),
            query,
        )
        return jobs

    async def get_job(
        self,
        company: str,
        posting_id: str,
    ) -> JobListing:
        """
        Fetch a single posting by ID from a Lever company.

        Raises
        ------
        httpx.HTTPStatusError
            If the posting is not found (404) or another HTTP error occurs.
        """
        url = f"{_BASE_URL}/{company}/{posting_id}"

        response = await self._request(url)
        raw = response.json()
        return _parse_posting(raw, company)
