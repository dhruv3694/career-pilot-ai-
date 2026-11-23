"""
Shared Pydantic schemas for the jobs services layer.

All job-related data models used across Greenhouse, Lever, SearXNG,
and the discovery orchestrator are defined here to ensure consistency.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class JobListing(BaseModel):
    """Unified job listing representation across all sources."""

    id: str
    title: str
    company: str
    location: str = ""
    description: str = ""
    url: str = ""
    source: str = ""
    posted_at: Optional[datetime] = None
    salary_range: Optional[str] = None
    work_mode: Optional[str] = None  # remote / hybrid / onsite
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    raw_data: dict = Field(default_factory=dict)


class SearchResult(BaseModel):
    """Generic web search result returned by SearXNG."""

    title: str
    url: str
    snippet: str = ""
    source: str = ""
    published_at: Optional[datetime] = None


class CareerEvent(BaseModel):
    """Representation of a career-related event (conference, meetup, etc.)."""

    id: str
    title: str
    description: str = ""
    url: str = ""
    location: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    event_type: str = ""  # conference, meetup, workshop, webinar, career_fair
    source: str = ""
    is_verified: bool = False


class JobSearchResponse(BaseModel):
    """Aggregated response returned by the discovery orchestrator."""

    jobs: list[JobListing] = Field(default_factory=list)
    total_results: int = 0
    sources_searched: list[str] = Field(default_factory=list)
    search_query: str = ""
    search_location: Optional[str] = None
    search_time_ms: float = 0.0
    errors: list[str] = Field(default_factory=list)
