"""
Job Discovery API Router.
Supports multi-source job aggregation across Greenhouse, Lever, SearXNG, and curated open listings.
Includes deduplication, verification status tracking, and saved job management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.jobs.discovery import JobDiscoveryService
from app.mcp.tools import tool_verify_public_listing
from app.memory.memory_manager import memory_manager

router = APIRouter(prefix="/jobs", tags=["Job Discovery"])
logger = logging.getLogger(__name__)

job_discovery_service = JobDiscoveryService()

class SaveJobRequest(BaseModel):
    job: Dict[str, Any]


class JobSearchRequest(BaseModel):
    query: str = Field(
        default="software engineer",
        min_length=2,
        max_length=120,
        description="Job title, keywords, or skills",
    )
    location: Optional[str] = Field(default=None, max_length=120, description="Location filter")
    work_mode: Optional[Literal["remote", "hybrid", "onsite"]] = None
    experience_level: Optional[str] = Field(default=None, max_length=30)
    source: Literal["greenhouse", "lever", "web", "all"] = "all"


@router.get("/search")
async def search_jobs(
    query: str = Query("software engineer", min_length=2, max_length=120, description="Job title, keywords, or skills"),
    location: Optional[str] = Query(None, max_length=120, description="Location filter"),
    work_mode: Optional[str] = Query(None, pattern=r"^(remote|hybrid|onsite)$"),
    experience_level: Optional[str] = Query(None, max_length=30),
    source: str = Query("all", pattern=r"^(greenhouse|lever|web|all)$"),
):
    """Search public job-board feeds and configured web search; never mix in sample listings."""
    if source == "web" and not settings.SEARXNG_ENABLED:
        return {
            "status": "unavailable",
            "query": query,
            "location": location,
            "jobs": [],
            "total_results": 0,
            "sources_searched": [],
            "errors": ["Web search is not configured. Set up a SearXNG instance to enable this source."],
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        }

    if source == "all":
        sources_to_query = ["greenhouse", "lever"]
        if settings.SEARXNG_ENABLED:
            sources_to_query.append("web")
    else:
        sources_to_query = [source]

    errors: list[str] = []
    response = None
    try:
        response = await job_discovery_service.discover(
            query=query,
            location=location,
            sources=sources_to_query,
            limit=20,
        )
        errors.extend(response.errors)
    except Exception as e:
        logger.warning("Job discovery failed: %s", str(e))
        errors.append(f"Job source request failed: {str(e)}")

    retrieved_at = datetime.now(timezone.utc).isoformat()
    jobs = []
    for job in response.jobs if response else []:
        if work_mode and (job.work_mode or "").lower() != work_mode.lower():
            continue
        if location and location.casefold() not in job.location.casefold() and job.work_mode != "remote":
            continue
        if experience_level and (job.experience_level or "").casefold() != experience_level.casefold():
            continue

        is_web_lead = job.source == "web"
        jobs.append({
            **job.model_dump(mode="json"),
            "id": f"{job.source}:{job.id}",
            "employer": job.company or "Employer not identified",
            "source_name": job.source,
            "source_url": (
                job.url if is_web_lead
                else f"https://boards.greenhouse.io/{job.company}" if job.source == "greenhouse"
                else f"https://jobs.lever.co/{job.company}" if job.source == "lever"
                else None
            ),
            "original_url": job.url or None,
            "verification_status": "search_result_lead" if is_web_lead else "public_listing_found",
            "retrieved_at": retrieved_at,
            "last_verified_at": None,
            "is_demo_data": False,
        })

    result_status = "partial_success" if jobs and errors else "success" if jobs else "no_results"
    if not jobs and errors:
        result_status = "unavailable"
    elif not jobs:
        errors.append("No listings matched the query from the selected public sources. No sample listings were added.")

    return {
        "status": result_status,
        "query": query,
        "location": location,
        "total_results": len(jobs),
        "jobs": jobs,
        "sources_searched": response.sources_searched if response else [],
        "retrieved_at": retrieved_at,
        "errors": errors,
    }


@router.post("/verify")
async def verify_job_url(url: str = Query(..., description="Job posting URL")):
    """Verify if external job listing is still live and reachable."""
    result = await tool_verify_public_listing(url)
    return result


@router.get("/saved")
async def get_saved_jobs():
    """Retrieve saved jobs from user long-term memory."""
    saved = memory_manager.get_saved_jobs()
    return {"saved_jobs": saved, "count": len(saved)}


@router.post("/save")
async def save_job(payload: SaveJobRequest):
    """Save job posting to long-term memory."""
    success = memory_manager.save_job(payload.job)
    return {"status": "success" if success else "already_saved", "saved": success}


@router.delete("/saved/{job_id}")
async def unsave_job(job_id: str):
    """Remove a job from long-term memory."""
    removed = memory_manager.remove_saved_job(job_id)
    return {"status": "success" if removed else "not_found", "removed": removed}



@router.post('/search')
async def search_jobs_post(payload: JobSearchRequest):
    return await search_jobs(
        query=payload.query,
        location=payload.location,
        work_mode=payload.work_mode,
        experience_level=payload.experience_level,
        source=payload.source,
    )
