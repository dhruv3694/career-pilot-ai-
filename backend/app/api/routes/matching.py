"""Evidence-based, deterministic job matching and saved comparison API."""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.resumes import RESUME_STORE
from app.core.database import get_db
from app.models.models import CandidateProfile, JobListing as JobListingRecord, JobMatch
from app.services.matching.matcher import JobMatcher

router = APIRouter(prefix="/matching", tags=["Job Matching"])
logger = logging.getLogger(__name__)
matcher = JobMatcher()


class CandidateMatchPayload(BaseModel):
    name: str = Field(default="", max_length=255)
    skills: list[str] = Field(default_factory=list, max_length=100)
    experience_years: float = Field(default=0.0, ge=0, le=80)
    summary: str = Field(default="", max_length=5000)
    preferred_roles: list[str] = Field(default_factory=list, max_length=20)
    preferred_locations: list[str] = Field(default_factory=list, max_length=20)
    open_to_remote: bool = True


class JobMatchPayload(BaseModel):
    id: str = Field(default="manual", max_length=255)
    title: str = Field(min_length=2, max_length=500)
    employer: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = Field(default=None, max_length=500)
    work_mode: Optional[str] = Field(default=None, pattern=r"^(remote|hybrid|onsite)$")
    required_skills: list[str] = Field(default_factory=list, max_length=100)
    preferred_skills: list[str] = Field(default_factory=list, max_length=100)
    description: str = Field(default="", max_length=20000)
    min_years: Optional[float] = Field(default=None, ge=0, le=80)
    source_name: Optional[str] = Field(default=None, max_length=100)
    source_url: Optional[str] = Field(default=None, max_length=1000)
    original_url: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("required_skills", "preferred_skills")
    @classmethod
    def normalize_skills(cls, skills: list[str]) -> list[str]:
        return list(dict.fromkeys(skill.strip() for skill in skills if skill.strip()))


class MatchCalculationRequest(BaseModel):
    resume_id: Optional[str] = Field(default=None, max_length=36)
    candidate: Optional[CandidateMatchPayload] = None
    job: JobMatchPayload


def _evidence_for(skill: str, profile: dict[str, Any], raw_text: str) -> dict[str, str] | None:
    skill_pattern = re.compile(rf"(?<!\w){re.escape(skill)}(?!\w)", re.IGNORECASE)
    for section_name, entries in (
        ("experience", profile.get("experience") or []),
        ("projects", profile.get("projects") or []),
        ("education", profile.get("education") or []),
        ("certifications", profile.get("certifications") or []),
        ("summary", [profile.get("summary") or ""]),
        ("skills", profile.get("skills") or []),
    ):
        for entry in entries:
            text = entry if isinstance(entry, str) else " ".join(
                str(value) for value in entry.values() if value
            ) if isinstance(entry, dict) else str(entry)
            if skill_pattern.search(text):
                return {"section": section_name, "text": text[:500]}

    for line in raw_text.splitlines():
        if skill_pattern.search(line):
            return {"section": "resume text (not in extracted profile)", "text": line.strip()[:500]}
    return None


def _build_skill_analysis(
    required: list[str],
    preferred: list[str],
    matched: list[str],
    profile: dict[str, Any],
    raw_text: str,
) -> list[dict[str, Any]]:
    matched_set = {skill.casefold() for skill in matched}
    items: list[dict[str, Any]] = []
    for skill in required + preferred:
        evidence = _evidence_for(skill, profile, raw_text)
        confirmed = skill.casefold() in matched_set
        items.append({
            "skill": skill,
            "importance": "required" if skill in required else "preferred",
            "status": "matched" if confirmed else "partial" if evidence else "missing",
            "evidence": evidence,
        })
    return items


@router.post("/calculate")
async def calculate_match(
    payload: MatchCalculationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Calculate a transparent score from supplied or parsed resume evidence and save it."""
    if not payload.resume_id and not payload.candidate:
        raise HTTPException(status_code=422, detail="Select a parsed resume or provide a candidate profile.")
    if not payload.job.required_skills:
        raise HTTPException(
            status_code=422,
            detail="Add at least one required skill from the job description before calculating a match.",
        )

    raw_text = ""
    resume_id = payload.resume_id
    if resume_id:
        resume = RESUME_STORE.get(resume_id)
        if not resume:
            raise HTTPException(
                status_code=404,
                detail="Resume not found in the current backend session. Re-parse it in Resume Studio.",
            )
        if not resume.get("profile_reviewed", False):
            raise HTTPException(
                status_code=409,
                detail="Review and save the extracted candidate profile in Resume Studio before comparing jobs.",
            )
        profile = resume["profile"]
        raw_text = resume.get("raw_text", "")
        candidate_id = resume_id
        candidate_summary = profile.get("summary") or ""
        candidate_skills = list(dict.fromkeys((profile.get("skills") or []) + (profile.get("soft_skills") or [])))
        candidate_experience = profile.get("experience") or []
        locations: list[str] = []
        open_to_remote = True
        candidate_name = profile.get("name") or ""
    else:
        assert payload.candidate is not None
        profile = payload.candidate.model_dump()
        candidate_id = str(uuid.uuid4())
        candidate_summary = payload.candidate.summary
        candidate_skills = payload.candidate.skills
        candidate_experience = [{"title": candidate_summary, "years": payload.candidate.experience_years}]
        locations = payload.candidate.preferred_locations
        open_to_remote = payload.candidate.open_to_remote
        candidate_name = payload.candidate.name

    candidate_for_score = {
        "skills": candidate_skills,
        "experience": candidate_experience,
        "summary": candidate_summary,
        "location_preferences": {
            "preferred_locations": locations,
            "open_to_remote": open_to_remote,
        },
    }
    job_for_score = {
        "title": payload.job.title,
        "description": payload.job.description,
        "required_skills": payload.job.required_skills,
        "preferred_skills": payload.job.preferred_skills,
        "requirements": {"min_years": payload.job.min_years or 0},
        "location": payload.job.location or "",
        "work_mode": payload.job.work_mode or "",
    }
    result = matcher.match(candidate_for_score, job_for_score)
    active_weights: dict[str, float] = {
        "required_skills": matcher.skill_weight,
    }
    if payload.job.preferred_skills:
        active_weights["preferred_skills"] = matcher.preferred_weight
    if payload.job.min_years is not None:
        active_weights["experience"] = matcher.experience_weight
    if candidate_summary.strip():
        active_weights["role_alignment"] = matcher.role_weight
    if locations and (payload.job.location or payload.job.work_mode):
        active_weights["location"] = matcher.location_weight
    total_weight = sum(active_weights.values())
    normalized_weights = {key: weight / total_weight for key, weight in active_weights.items()}
    category_scores = {
        "required_skills": result.skill_coverage_score,
        "preferred_skills": result.preferred_coverage_score,
        "experience": result.experience_score,
        "role_alignment": result.role_alignment_score,
        "location": result.location_score,
    }
    adjusted_score = round(
        sum(category_scores[key] * weight for key, weight in normalized_weights.items()),
        2,
    )
    result = result.model_copy(update={
        "overall_score": adjusted_score,
        "score_breakdown": {
            key: round(category_scores[key] * weight, 2)
            for key, weight in normalized_weights.items()
        },
    })
    skill_analysis = _build_skill_analysis(
        payload.job.required_skills,
        payload.job.preferred_skills,
        result.matched_skills,
        profile,
        raw_text,
    )
    missing_required = [
        item["skill"] for item in skill_analysis
        if item["importance"] == "required" and item["status"] == "missing"
    ]
    partial_skills = [item["skill"] for item in skill_analysis if item["status"] == "partial"]

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    candidate_record = await db.get(CandidateProfile, candidate_id)
    if candidate_record is None:
        candidate_record = CandidateProfile(
            id=candidate_id,
            name=candidate_name,
            summary=candidate_summary,
        )
        db.add(candidate_record)
    else:
        candidate_record.name = candidate_name
        candidate_record.summary = candidate_summary

    external_id = payload.job.id if payload.job.id != "manual" else f"manual:{uuid.uuid4()}"
    job_record = await db.scalar(
        select(JobListingRecord)
        .where(JobListingRecord.external_id == external_id)
        .where(JobListingRecord.source_name == (payload.job.source_name or "user_provided"))
        .limit(1)
    )
    if job_record is None:
        job_record = JobListingRecord(
            external_id=external_id,
            title=payload.job.title,
            employer=payload.job.employer,
            location=payload.job.location,
            work_mode=payload.job.work_mode,
            required_skills=payload.job.required_skills,
            preferred_skills=payload.job.preferred_skills,
            description=payload.job.description,
            source_name=payload.job.source_name or "user_provided",
            source_url=payload.job.source_url,
            original_url=payload.job.original_url,
            retrieval_timestamp=now,
            verification_status=(
                "user_provided"
                if not payload.job.source_name or payload.job.source_name == "user_provided"
                else "public_listing_found"
            ),
            is_demo_data=False,
        )
        db.add(job_record)

    await db.flush()
    saved = JobMatch(
        candidate_id=candidate_id,
        job_id=job_record.id,
        overall_score=result.overall_score,
        required_skill_coverage=result.skill_coverage_score,
        preferred_skill_coverage=result.preferred_coverage_score,
        experience_match=result.experience_score,
        role_alignment=result.role_alignment_score,
        location_match=result.location_score,
        skill_matches=skill_analysis,
        skill_gaps=[gap.model_dump() for gap in result.skill_gaps],
        score_breakdown=result.score_breakdown,
        llm_explanation=None,
    )
    db.add(saved)
    await db.flush()

    experience_evidence = []
    for section in ("experience", "projects"):
        for item in profile.get(section, []) or []:
            if isinstance(item, dict):
                text = " — ".join(str(value) for value in item.values() if value)
                if text.strip():
                    experience_evidence.append({"section": section, "text": text[:600]})

    return {
        "status": "success",
        "comparison_id": saved.id,
        "saved": True,
        "candidate": {
            "resume_id": resume_id,
            "name": candidate_name or "Candidate profile",
            "skills": candidate_skills,
        },
        "job": {
            "id": job_record.id,
            "external_id": external_id,
            "title": job_record.title,
            "employer": job_record.employer,
            "source_name": job_record.source_name,
            "original_url": job_record.original_url,
        },
        "match": result.model_dump(),
        "skill_analysis": skill_analysis,
        "missing_required_skills": missing_required,
        "partial_skills": partial_skills,
        "experience_evidence": experience_evidence[:12],
        "education_evidence": profile.get("education", []),
        "certification_evidence": profile.get("certifications", []),
        "scoring": {
            "method": "deterministic",
            "weights": normalized_weights,
            "evaluated_categories": list(normalized_weights),
            "not_assessed_categories": [
                name for name in category_scores if name not in normalized_weights
            ],
            "explanation": "The score uses exact extracted-skill matches and only scores other categories when the resume and job provide enough information. Partial resume mentions are displayed as evidence but do not count as confirmed skill matches. Active weights are normalized for this comparison; weights are product heuristics, not an industry standard.",
        },
        "interpretation": {
            "status": "not_requested",
            "summary": "No external AI interpretation was requested. Candidate data was not sent to an LLM provider.",
            "provider_used": None,
        },
        "potential_concerns": [
            f"Required skill not found in the extracted profile: {skill}"
            for skill in missing_required
        ],
        "resume_improvements": [
            f"If supported by your actual experience, add specific evidence for {skill} to the relevant experience or project section."
            for skill in missing_required
        ],
        "learning_actions": [
            f"Build a small project or complete guided practice using {skill}."
            for skill in missing_required
        ],
        "disclaimer": "This deterministic comparison is informational only. It is not an official ATS score and does not predict an employer's screening decision.",
    }


@router.get("/saved")
async def list_saved_matches(
    resume_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Return database-persisted comparisons, optionally filtered to one parsed resume."""
    query = (
        select(JobMatch, JobListingRecord)
        .join(JobListingRecord, JobListingRecord.id == JobMatch.job_id)
        .order_by(JobMatch.created_at.desc())
        .limit(100)
    )
    if resume_id:
        query = query.where(JobMatch.candidate_id == resume_id)
    rows = (await db.execute(query)).all()
    return {
        "comparisons": [
            {
                "id": match.id,
                "resume_id": match.candidate_id,
                "job": {
                    "id": job.id,
                    "title": job.title,
                    "employer": job.employer,
                    "location": job.location,
                    "work_mode": job.work_mode,
                    "required_skills": job.required_skills or [],
                    "preferred_skills": job.preferred_skills or [],
                    "description": job.description or "",
                    "source_name": job.source_name,
                    "original_url": job.original_url,
                    "verification_status": job.verification_status,
                    "retrieved_at": job.retrieval_timestamp.isoformat() if job.retrieval_timestamp else None,
                    "is_demo_data": job.is_demo_data,
                },
                "overall_score": match.overall_score,
                "skill_matches": match.skill_matches or [],
                "skill_gaps": match.skill_gaps or [],
                "score_breakdown": match.score_breakdown or {},
                "created_at": match.created_at.isoformat() if match.created_at else None,
            }
            for match, job in rows
        ],
        "count": len(rows),
    }


@router.delete("/saved/{comparison_id}")
async def delete_saved_match(comparison_id: str, db: AsyncSession = Depends(get_db)):
    saved = await db.get(JobMatch, comparison_id)
    if saved is None:
        raise HTTPException(status_code=404, detail="Saved comparison not found.")
    await db.delete(saved)
    return {"status": "success", "deleted": True}
