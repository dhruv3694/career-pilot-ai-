"""
Pydantic v2 schemas for job listing and matching operations.
"""

from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JobListingSchema(BaseModel):
    """Full job listing schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: Optional[str] = None
    title: str
    employer: Optional[str] = None
    location: Optional[str] = None
    work_mode: Optional[str] = None
    employment_type: Optional[str] = None
    experience_min: Optional[int] = None
    experience_max: Optional[int] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    description: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    original_url: Optional[str] = None
    date_discovered: Optional[datetime] = None
    retrieval_timestamp: Optional[datetime] = None
    publication_date: Optional[date] = None
    closing_date: Optional[date] = None
    verification_status: str = "pending"
    last_checked: Optional[datetime] = None
    is_demo_data: bool = False
    created_at: datetime


class JobSearchRequest(BaseModel):
    """Request body for searching job listings."""

    query: str = Field(..., min_length=1, max_length=500)
    location: Optional[str] = None
    work_mode: Optional[str] = Field(default=None, description="remote, hybrid, onsite")
    employment_type: Optional[str] = Field(default=None, description="full-time, part-time, contract, internship")
    skills: Optional[List[str]] = None
    experience_level: Optional[str] = Field(default=None, description="entry, mid, senior, lead")
    sources: Optional[List[str]] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class JobSearchResponse(BaseModel):
    """Response from a job search query."""

    jobs: List[JobListingSchema]
    total: int
    page: int
    page_size: int
    sources_used: List[str]
    sources_failed: List[str] = Field(default_factory=list)


class JobMatchSchema(BaseModel):
    """Full job match schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    job_id: str
    overall_score: float
    required_skill_coverage: Optional[float] = None
    preferred_skill_coverage: Optional[float] = None
    experience_match: Optional[float] = None
    role_alignment: Optional[float] = None
    location_match: Optional[float] = None
    skill_matches: Optional[List[str]] = None
    skill_gaps: Optional[List[str]] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    llm_explanation: Optional[str] = None
    created_at: datetime


class JobMatchRequest(BaseModel):
    """Request to compute a match between a candidate and a job."""

    candidate_id: str
    job_id: str


class JobMatchResponse(BaseModel):
    """Response from a job match computation."""

    match: JobMatchSchema
    job: Optional[JobListingSchema] = None
    score_breakdown: Optional[Dict[str, Any]] = None
    explanation: Optional[str] = None
    recommendations: Optional[List[str]] = None
