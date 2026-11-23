"""
Job discovery orchestrator.

Aggregates job listings from Greenhouse, Lever, and SearXNG web search.
De-duplicates, ranks by relevance, and returns a unified response.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Optional

from app.services.jobs.greenhouse import GreenhouseAdapter
from app.services.jobs.lever import LeverAdapter
from app.services.jobs.schemas import JobListing, JobSearchResponse
from app.services.jobs.searxng import SearXNGAdapter

logger = logging.getLogger(__name__)

_DEFAULT_GREENHOUSE_BOARDS: list[str] = ["github", "figma", "airbnb"]
_DEFAULT_LEVER_COMPANIES: list[str] = ["netflix", "twitch"]


def _normalise(text: str) -> str:
    """Lowercase, strip, and collapse whitespace for comparison."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _tokenise(text: str) -> set[str]:
    """Split text into a set of lowercase alphanumeric tokens."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _relevance_score(job: JobListing, query_tokens: set[str]) -> float:
    """
    Compute a simple relevance score for ranking.

    Score components:
    - Title token overlap (weighted ×3)
    - Description token overlap (weighted ×1)
    - Location token overlap (weighted ×1)
    """
    if not query_tokens:
        return 0.0

    title_tokens = _tokenise(job.title)
    desc_tokens = _tokenise(job.description[:500])  # limit for perf
    loc_tokens = _tokenise(job.location)

    title_overlap = len(query_tokens & title_tokens)
    desc_overlap = len(query_tokens & desc_tokens)
    loc_overlap = len(query_tokens & loc_tokens)

    total = (title_overlap * 3) + desc_overlap + loc_overlap
    return total / max(len(query_tokens), 1)


class JobDiscoveryService:
    """
    Orchestrates job searches across multiple sources and returns a
    deduplicated, relevance-ranked response.
    """

    def __init__(self) -> None:
        self._greenhouse = GreenhouseAdapter()
        self._lever = LeverAdapter()
        self._searxng = SearXNGAdapter()

    async def close(self) -> None:
        """Release resources held by adapters."""
        await asyncio.gather(
            self._greenhouse.close(),
            self._lever.close(),
            self._searxng.close(),
            return_exceptions=True,
        )

    # ------------------------------------------------------------------
    # Source-specific helpers
    # ------------------------------------------------------------------

    async def _search_greenhouse(
        self,
        query: str,
        boards: list[str],
    ) -> tuple[list[JobListing], list[str]]:
        """Fetch jobs and collect board-specific failures."""
        tasks = [self._greenhouse.search(board, query) for board in boards]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        jobs: list[JobListing] = []
        errors: list[str] = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Greenhouse board '%s' failed: %s",
                    boards[idx],
                    result,
                )
                errors.append(f"Greenhouse board {boards[idx]} failed: {result}")
                continue
            jobs.extend(result)
        return jobs, errors

    async def _search_lever(
        self,
        query: str,
        companies: list[str],
    ) -> tuple[list[JobListing], list[str]]:
        """Fetch jobs and collect company-specific failures."""
        tasks = [self._lever.search(company, query) for company in companies]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        jobs: list[JobListing] = []
        errors: list[str] = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Lever company '%s' failed: %s",
                    companies[idx],
                    result,
                )
                errors.append(f"Lever company {companies[idx]} failed: {result}")
                continue
            jobs.extend(result)
        return jobs, errors

    async def _search_web(
        self,
        query: str,
        location: str | None = None,
    ) -> tuple[list[JobListing], list[str]]:
        """Search for jobs via SearXNG web meta-search."""
        try:
            jobs = await self._searxng.search_jobs(query, location)
            return jobs, []
        except Exception as exc:
            logger.error("SearXNG job search failed: %s", exc)
            return [], [f"SearXNG search failed: {exc}"]

    # ------------------------------------------------------------------
    # De-duplication and ranking
    # ------------------------------------------------------------------

    def _deduplicate(self, jobs: list[JobListing]) -> list[JobListing]:
        """
        Remove duplicate listings based on normalised title + company.

        When duplicates are found the first occurrence is kept (source
        priority is determined by insertion order from
        ``asyncio.gather``).
        """
        seen: set[str] = set()
        unique: list[JobListing] = []
        for job in jobs:
            key = f"{_normalise(job.title)}||{_normalise(job.company)}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(job)
        return unique

    def _rank(
        self,
        jobs: list[JobListing],
        query: str,
    ) -> list[JobListing]:
        """Sort jobs by relevance to the search query (descending)."""
        query_tokens = _tokenise(query)
        if not query_tokens:
            return jobs
        return sorted(
            jobs,
            key=lambda j: _relevance_score(j, query_tokens),
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Main entry-point
    # ------------------------------------------------------------------

    async def discover(
        self,
        query: str,
        location: str | None = None,
        sources: list[str] | None = None,
        greenhouse_boards: list[str] | None = None,
        lever_companies: list[str] | None = None,
        limit: int = 50,
    ) -> JobSearchResponse:
        """
        Discover jobs across configured sources.

        Parameters
        ----------
        query:
            Keywords to search for (e.g. "python backend developer").
        location:
            Optional location filter.
        sources:
            Which sources to query.  Defaults to all:
            ``["greenhouse", "lever", "web"]``.
        greenhouse_boards:
            Override the list of Greenhouse board tokens.
        lever_companies:
            Override the list of Lever company slugs.
        limit:
            Maximum number of results to return.

        Returns
        -------
        JobSearchResponse
        """
        start_time = time.perf_counter()

        if sources is None:
            sources = ["greenhouse", "lever", "web"]

        boards = greenhouse_boards or _DEFAULT_GREENHOUSE_BOARDS
        companies = lever_companies or _DEFAULT_LEVER_COMPANIES

        # Build coroutines for requested sources.
        tasks_list: list[tuple[str, asyncio.Task]] = []  # type: ignore[type-arg]

        if "greenhouse" in sources:
            tasks_list.append(
                ("greenhouse", asyncio.ensure_future(self._search_greenhouse(query, boards)))
            )
        if "lever" in sources:
            tasks_list.append(
                ("lever", asyncio.ensure_future(self._search_lever(query, companies)))
            )
        if "web" in sources:
            tasks_list.append(
                ("web", asyncio.ensure_future(self._search_web(query, location)))
            )

        # Wait for all tasks (never raises — exceptions are captured).
        if tasks_list:
            await asyncio.gather(
                *(t for _, t in tasks_list), return_exceptions=True
            )

        # Collect results and errors.
        all_jobs: list[JobListing] = []
        sources_searched: list[str] = []
        errors: list[str] = []

        for source_name, task in tasks_list:
            sources_searched.append(source_name)
            try:
                result = task.result()
                if isinstance(result, tuple):
                    jobs, source_errors = result
                    all_jobs.extend(jobs)
                    errors.extend(source_errors)
                elif isinstance(result, Exception):
                    errors.append(f"{source_name}: {result}")
            except Exception as exc:
                errors.append(f"{source_name}: {exc}")

        # Post-process.
        all_jobs = self._deduplicate(all_jobs)
        all_jobs = self._rank(all_jobs, query)
        all_jobs = all_jobs[:limit]

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        response = JobSearchResponse(
            jobs=all_jobs,
            total_results=len(all_jobs),
            sources_searched=sources_searched,
            search_query=query,
            search_location=location,
            search_time_ms=round(elapsed_ms, 2),
            errors=errors,
        )

        logger.info(
            "Job discovery for %r completed in %.0fms: %d jobs from %s "
            "(%d errors).",
            query,
            elapsed_ms,
            response.total_results,
            sources_searched,
            len(errors),
        )
        return response
