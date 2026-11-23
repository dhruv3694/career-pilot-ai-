"""
Pydantic v2 schemas for resume-related operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ResumeUploadResponse(BaseModel):
    """Response returned after a successful resume upload."""

    model_config = ConfigDict(from_attributes=True)

    resume_id: str
    candidate_id: str
    filename: str
    file_type: str
    file_size: int
    extraction_quality: Optional[float] = None
    is_scanned: bool = False
    ocr_used: bool = False
    message: str = "Resume uploaded successfully"


class CandidateProfileSchema(BaseModel):
    """Full candidate profile schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    raw_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CandidateProfileCreateRequest(BaseModel):
    """Request body for creating a new candidate profile."""

    name: str = Field(..., min_length=1, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None


class ExtractedSection(BaseModel):
    """A section extracted from a resume document."""

    section_name: str
    content: str
    confidence: float = Field(ge=0.0, le=1.0)


class ATSCheckResult(BaseModel):
    """Result of a single ATS compatibility check."""

    check_name: str
    passed: bool
    score: float = Field(ge=0.0)
    max_score: float = Field(ge=0.0)
    details: str
    severity: str = Field(default="info", description="One of: info, warning, critical")


class ATSReport(BaseModel):
    """Full ATS compatibility report for a resume."""

    overall_score: float = Field(ge=0.0, le=100.0)
    checks: List[ATSCheckResult]
    keyword_coverage: float = Field(ge=0.0, le=1.0)
    section_completeness: Dict[str, bool]
    formatting_warnings: List[str]
    suggestions: List[str]


class ResumeAnalysisRequest(BaseModel):
    """Request to analyze / assess a resume."""

    resume_id: str
    job_id: Optional[str] = None


class ResumeEvidenceSchema(BaseModel):
    """Schema for resume evidence entries."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    assessment_id: str
    claim: str
    evidence_text: str
    source_section: Optional[str] = None
    confidence: float
    is_verified: bool
    created_at: datetime


class ResumeAnalysisResponse(BaseModel):
    """Response from a resume analysis / assessment run."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    resume_id: str
    job_id: Optional[str] = None
    overall_score: float
    section_scores: Optional[Dict[str, Any]] = None
    keyword_coverage: Optional[float] = None
    formatting_warnings: Optional[List[str]] = None
    suggestions: Optional[List[str]] = None
    evidence_refs: Optional[List[Dict[str, Any]]] = None
    llm_provider_used: Optional[str] = None
    assessment_type: str
    evidence_entries: Optional[List[ResumeEvidenceSchema]] = None
    created_at: datetime
