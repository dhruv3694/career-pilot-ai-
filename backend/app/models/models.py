"""
SQLAlchemy 2.0 ORM models for CareerPilot AI.

All models use ``Mapped[]`` type annotations and the declarative-base pattern.
JSON columns store structured data (lists, dicts) as native JSON in SQLite.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def _generate_uuid() -> str:
    """Generate a UUID4 string for use as a primary key."""
    return str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════════
# Candidate & Resume Models
# ═══════════════════════════════════════════════════════════════════════════


class CandidateProfile(Base):
    """Core profile for a candidate / job seeker."""

    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    github_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    resumes: Mapped[List["ResumeDocument"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    preferences: Mapped[List["CareerPreference"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    job_matches: Mapped[List["JobMatch"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    skill_assessments: Mapped[List["SkillAssessment"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    learning_plans: Mapped[List["LearningPlan"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    memory_entries: Mapped[List["MemoryEntry"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    workflow_runs: Mapped[List["WorkflowRun"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    approval_requests: Mapped[List["ApprovalRequest"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_candidate_profiles_email", "email"),
    )


class ResumeDocument(Base):
    """Uploaded resume document and its extracted text."""

    __tablename__ = "resume_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    extraction_quality: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ocr_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    upload_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="resumes")
    assessments: Mapped[List["ResumeAssessment"]] = relationship(back_populates="resume", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_resume_documents_candidate_id", "candidate_id"),
    )


class ResumeAssessment(Base):
    """Assessment / scoring of a resume, optionally against a job listing."""

    __tablename__ = "resume_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    resume_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_documents.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_listings.id", ondelete="SET NULL"), nullable=True)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    section_scores: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    keyword_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    formatting_warnings: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    suggestions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    evidence_refs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    llm_provider_used: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    assessment_type: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    resume: Mapped["ResumeDocument"] = relationship(back_populates="assessments")
    job: Mapped[Optional["JobListing"]] = relationship(back_populates="resume_assessments")
    evidence_entries: Mapped[List["ResumeEvidence"]] = relationship(back_populates="assessment", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_resume_assessments_resume_id", "resume_id"),
        Index("ix_resume_assessments_job_id", "job_id"),
    )


class ResumeEvidence(Base):
    """Evidence backing a claim made in a resume assessment."""

    __tablename__ = "resume_evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    assessment_id: Mapped[str] = mapped_column(String(36), ForeignKey("resume_assessments.id", ondelete="CASCADE"), nullable=False)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_section: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    assessment: Mapped["ResumeAssessment"] = relationship(back_populates="evidence_entries")

    __table_args__ = (
        Index("ix_resume_evidence_assessment_id", "assessment_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Career Preferences
# ═══════════════════════════════════════════════════════════════════════════


class CareerPreference(Base):
    """Candidate's career preferences and constraints."""

    __tablename__ = "career_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    target_roles: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    preferred_locations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # remote, hybrid, onsite
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # full-time, part-time, contract
    min_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_salary: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    industries: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="preferences")

    __table_args__ = (
        Index("ix_career_preferences_candidate_id", "candidate_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Job Listings & Matching
# ═══════════════════════════════════════════════════════════════════════════


class JobListing(Base):
    """A job posting discovered from an external source."""

    __tablename__ = "job_listings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    employer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    work_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    experience_min: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    experience_max: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    required_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    preferred_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    original_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    date_discovered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    retrieval_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    publication_date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    closing_date: Mapped[Optional[date]] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    last_checked: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_demo_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    resume_assessments: Mapped[List["ResumeAssessment"]] = relationship(back_populates="job")
    matches: Mapped[List["JobMatch"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    interview_sessions: Mapped[List["InterviewSession"]] = relationship(back_populates="job")

    __table_args__ = (
        Index("ix_job_listings_title", "title"),
        Index("ix_job_listings_employer", "employer"),
        Index("ix_job_listings_external_id", "external_id"),
        Index("ix_job_listings_verification_status", "verification_status"),
    )


class JobSource(Base):
    """Configuration for a job listing source / scraper."""

    __tablename__ = "job_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # api, scraper, rss
    base_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    api_key_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


class JobMatch(Base):
    """Computed match between a candidate and a job listing."""

    __tablename__ = "job_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), ForeignKey("job_listings.id", ondelete="CASCADE"), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    required_skill_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    preferred_skill_coverage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    experience_match: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    role_alignment: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    location_match: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    skill_matches: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    skill_gaps: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    score_breakdown: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    llm_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="job_matches")
    job: Mapped["JobListing"] = relationship(back_populates="matches")

    __table_args__ = (
        Index("ix_job_matches_candidate_id", "candidate_id"),
        Index("ix_job_matches_job_id", "job_id"),
        Index("ix_job_matches_overall_score", "overall_score"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Skills
# ═══════════════════════════════════════════════════════════════════════════


class SkillAssessment(Base):
    """Assessment of a candidate's proficiency in a specific skill."""

    __tablename__ = "skill_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    proficiency_level: Mapped[str] = mapped_column(String(50), nullable=False)  # beginner, intermediate, advanced, expert
    evidence_sources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="skill_assessments")

    __table_args__ = (
        Index("ix_skill_assessments_candidate_id", "candidate_id"),
        Index("ix_skill_assessments_skill_name", "skill_name"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Career Events
# ═══════════════════════════════════════════════════════════════════════════


class CareerEvent(Base):
    """A career-related event (job fair, workshop, webinar, etc.)."""

    __tablename__ = "career_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    organizer: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    event_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    event_end_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    venue: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_online: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    eligibility: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    target_roles: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    registration_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    registration_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    retrieval_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_career_events_event_date", "event_date"),
        Index("ix_career_events_name", "name"),
        Index("ix_career_events_external_id", "external_id"),
    )


class EventSource(Base):
    """Configuration for a career event source."""

    __tablename__ = "event_sources"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    base_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ═══════════════════════════════════════════════════════════════════════════
# Learning Plans
# ═══════════════════════════════════════════════════════════════════════════


class LearningPlan(Base):
    """Personalized learning plan for skill development."""

    __tablename__ = "learning_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    current_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    target_skills: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    timeline_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="learning_plans")
    milestones: Mapped[List["LearningMilestone"]] = relationship(back_populates="plan", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_learning_plans_candidate_id", "candidate_id"),
        Index("ix_learning_plans_status", "status"),
    )


class LearningMilestone(Base):
    """A milestone within a learning plan."""

    __tablename__ = "learning_milestones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("learning_plans.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    skill_area: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    resources: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    target_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    plan: Mapped["LearningPlan"] = relationship(back_populates="milestones")

    __table_args__ = (
        Index("ix_learning_milestones_plan_id", "plan_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Interview Practice
# ═══════════════════════════════════════════════════════════════════════════


class InterviewSession(Base):
    """An interview practice session."""

    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    job_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("job_listings.id", ondelete="SET NULL"), nullable=True)
    session_type: Mapped[str] = mapped_column(String(50), nullable=False)  # behavioral, technical, system_design
    questions: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    responses: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    evaluations: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    overall_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="interview_sessions")
    job: Mapped[Optional["JobListing"]] = relationship(back_populates="interview_sessions")

    __table_args__ = (
        Index("ix_interview_sessions_candidate_id", "candidate_id"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Memory / Preferences
# ═══════════════════════════════════════════════════════════════════════════


class MemoryEntry(Base):
    """Persistent memory entry for a candidate (preferences, context, etc.)."""

    __tablename__ = "memory_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    memory_type: Mapped[str] = mapped_column(String(50), nullable=False)  # preference, context, interaction
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    source: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="memory_entries")

    __table_args__ = (
        Index("ix_memory_entries_candidate_id", "candidate_id"),
        Index("ix_memory_entries_key", "key"),
        Index("ix_memory_entries_memory_type", "memory_type"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Workflow & Agent Orchestration
# ═══════════════════════════════════════════════════════════════════════════


class WorkflowRun(Base):
    """A single execution of a multi-agent workflow."""

    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="SET NULL"), nullable=True)
    workflow_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    candidate: Mapped[Optional["CandidateProfile"]] = relationship(back_populates="workflow_runs")
    agent_executions: Mapped[List["AgentExecution"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")
    agent_messages: Mapped[List["AgentMessage"]] = relationship(back_populates="workflow", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_workflow_runs_status", "status"),
        Index("ix_workflow_runs_workflow_type", "workflow_type"),
        Index("ix_workflow_runs_candidate_id", "candidate_id"),
    )


class AgentExecution(Base):
    """Execution record for a single agent within a workflow."""

    __tablename__ = "agent_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    agent_name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    input_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    workflow: Mapped["WorkflowRun"] = relationship(back_populates="agent_executions")
    tool_executions: Mapped[List["ToolExecution"]] = relationship(back_populates="agent_execution", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_agent_executions_workflow_id", "workflow_id"),
        Index("ix_agent_executions_agent_name", "agent_name"),
    )


class AgentMessage(Base):
    """Inter-agent message within a workflow."""

    __tablename__ = "agent_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False)
    from_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    to_agent: Mapped[str] = mapped_column(String(255), nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    workflow: Mapped["WorkflowRun"] = relationship(back_populates="agent_messages")

    __table_args__ = (
        Index("ix_agent_messages_workflow_id", "workflow_id"),
    )


class ToolExecution(Base):
    """Record of a tool invocation by an agent."""

    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    agent_execution_id: Mapped[str] = mapped_column(String(36), ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(255), nullable=False)
    input_params: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    # Relationships
    agent_execution: Mapped["AgentExecution"] = relationship(back_populates="tool_executions")

    __table_args__ = (
        Index("ix_tool_executions_agent_execution_id", "agent_execution_id"),
        Index("ix_tool_executions_tool_name", "tool_name"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Provider Telemetry
# ═══════════════════════════════════════════════════════════════════════════


class ProviderExecution(Base):
    """Telemetry record for an LLM provider call."""

    __tablename__ = "provider_executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    provider_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prompt_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="success", nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_provider_executions_provider_name", "provider_name"),
        Index("ix_provider_executions_created_at", "created_at"),
    )


# ═══════════════════════════════════════════════════════════════════════════
# Approval Requests (Human-in-the-Loop)
# ═══════════════════════════════════════════════════════════════════════════


class ApprovalRequest(Base):
    """Human-in-the-loop approval request from an agent."""

    __tablename__ = "approval_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_generate_uuid)
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidate_profiles.id", ondelete="CASCADE"), nullable=False)
    request_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    reviewer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    candidate: Mapped["CandidateProfile"] = relationship(back_populates="approval_requests")

    __table_args__ = (
        Index("ix_approval_requests_status", "status"),
        Index("ix_approval_requests_candidate_id", "candidate_id"),
    )
