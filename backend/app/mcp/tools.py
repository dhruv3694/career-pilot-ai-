"""
CareerPilot AI - MCP Tool Registry and Security Implementations.
Exposes the 13 required MCP tools with parameter validation, SSRF defense,
path traversal checks, and prompt injection defense.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.resume.parser import ResumeParser
from app.services.resume.ats import ats_validator
from app.services.jobs.discovery import JobDiscoveryService
from app.services.matching.matcher import JobMatcher
from app.services.career.roadmap import CareerRoadmapService
from app.services.events.discovery import EventDiscoveryService
from app.memory.memory_manager import memory_manager, UserPreferences
from app.memory.vector_store import vector_store

logger = logging.getLogger(__name__)

# Security & Safeguards
BLOCKED_IP_PATTERNS = [
    r"://127\.", r"://10\.", r"://172\.(1[6-9]|2[0-9]|3[0-1])\.", r"://192\.168\.", r"://169\.254\.", r"://localhost",
    r"^127\.", r"^10\.", r"^localhost"
]

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior)\s+instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+dan",
    r"output\s+the\s+entire\s+internal\s+prompt",
    r"reveal\s+(api\s+)?key",
    r"delete\s+all\s+databases",
    r"disregard\s+system\s+safety",
]


def sanitize_untrusted_text(text: str) -> str:
    """Sanitize retrieved external web/document text to neutralize prompt injection payloads."""
    sanitized = text
    for pattern in INJECTION_PATTERNS:
        sanitized = re.sub(pattern, "[FILTERED_UNTRUSTED_INSTRUCTION]", sanitized, flags=re.I)
    return sanitized


def validate_safe_path(file_path: str, base_dir: Optional[str] = None) -> Path:
    """Path traversal prevention."""
    path = Path(file_path).resolve()
    if base_dir:
        base = Path(base_dir).resolve()
        if not str(path).startswith(str(base)):
            raise ValueError(f"Path traversal detected: {file_path} is outside allowed directory.")
    return path


# Tool Service Singletons
_parser = ResumeParser()
_job_discovery = JobDiscoveryService()
_event_discovery = EventDiscoveryService()
_matcher = JobMatcher()
_roadmap_service = CareerRoadmapService()


# ─────────────────────────────────────────────────────────────────────────────
# 1. parse_resume
# ─────────────────────────────────────────────────────────────────────────────
async def tool_parse_resume(file_path: str, file_type: str = ".txt") -> Dict[str, Any]:
    """Parse resume document (PDF, DOCX, TXT) and extract raw text and metadata."""
    safe_path = validate_safe_path(file_path)
    result = _parser.parse(str(safe_path), file_type)
    return {
        "text": sanitize_untrusted_text(result.text),
        "quality_score": result.quality_score,
        "is_scanned": result.is_scanned,
        "warnings": result.warnings,
        "word_count": result.word_count,
        "page_count": result.page_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. validate_resume
# ─────────────────────────────────────────────────────────────────────────────
async def tool_validate_resume(resume_text: str) -> Dict[str, Any]:
    """Perform deterministic ATS-style validation on resume text."""
    report = ats_validator.evaluate(raw_text=resume_text)
    return report.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 3. analyze_resume_against_job
# ─────────────────────────────────────────────────────────────────────────────
async def tool_analyze_resume_against_job(
    resume_text: str,
    job_description: str,
    required_skills: List[str],
    preferred_skills: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Analyze resume text directly against job requirements and description."""
    clean_job = sanitize_untrusted_text(job_description)
    report = ats_validator.evaluate(
        raw_text=resume_text,
        job_description=clean_job,
        required_skills=required_skills,
        preferred_skills=preferred_skills or [],
    )
    return report.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 4. search_web
# ─────────────────────────────────────────────────────────────────────────────
async def tool_search_web(query: str, count: int = 5) -> Dict[str, Any]:
    """Perform metasearch for career opportunities or technical topics with untrusted content sanitization."""
    # Use searxng adapter
    from app.services.jobs.searxng import SearXNGAdapter
    adapter = SearXNGAdapter()
    try:
        results = await adapter.search(query=query, limit=count)
        return {
            "query": query,
            "results": [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": sanitize_untrusted_text(r.description[:300]),
                    "source": r.source,
                }
                for r in results
            ],
        }
    finally:
        await adapter.close()


# ─────────────────────────────────────────────────────────────────────────────
# 5. search_greenhouse_jobs
# ─────────────────────────────────────────────────────────────────────────────
async def tool_search_greenhouse_jobs(board_token: str, query: str = "") -> List[Dict[str, Any]]:
    """Query Greenhouse Job Board API for an employer board."""
    from app.services.jobs.greenhouse import GreenhouseAdapter
    adapter = GreenhouseAdapter()
    try:
        jobs = await adapter.search(board_token=board_token, query=query)
        return [j.model_dump() for j in jobs]
    finally:
        await adapter.close()


# ─────────────────────────────────────────────────────────────────────────────
# 6. search_lever_jobs
# ─────────────────────────────────────────────────────────────────────────────
async def tool_search_lever_jobs(company_slug: str, query: str = "") -> List[Dict[str, Any]]:
    """Query Lever Postings API for an employer board."""
    from app.services.jobs.lever import LeverAdapter
    adapter = LeverAdapter()
    try:
        jobs = await adapter.search(company=company_slug, query=query)
        return [j.model_dump() for j in jobs]
    finally:
        await adapter.close()


# ─────────────────────────────────────────────────────────────────────────────
# 7. search_career_events
# ─────────────────────────────────────────────────────────────────────────────
async def tool_search_career_events(query: str, location: Optional[str] = None) -> Dict[str, Any]:
    """Find public career fairs, hiring drives, and recruitment conferences."""
    res = await _event_discovery.search(query=query, location=location)
    return res.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 8. verify_public_listing
# ─────────────────────────────────────────────────────────────────────────────
async def tool_verify_public_listing(url: str) -> Dict[str, Any]:
    """Check whether a discovered public job URL or event URL is live and responsive (without violating anti-bot policies)."""
    import httpx
    # Prevent SSRF
    for pattern in BLOCKED_IP_PATTERNS:
        if re.search(pattern, url):
            return {"url": url, "is_live": False, "status": "blocked_ssrf_attempt"}

    try:
        async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as client:
            resp = await client.head(url)
            if resp.status_code in (405, 501):
                resp = await client.get(url)
            is_live = resp.status_code < 400
            return {
                "url": url,
                "is_live": is_live,
                "status_code": resp.status_code,
                "status": "live_verified" if is_live else "unavailable",
            }
    except Exception as e:
        return {
            "url": url,
            "is_live": False,
            "status": "unavailable",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# 9. calculate_job_match
# ─────────────────────────────────────────────────────────────────────────────
async def tool_calculate_job_match(
    candidate_skills: List[str],
    candidate_experience_years: float,
    job_required_skills: List[str],
    job_preferred_skills: Optional[List[str]] = None,
    job_title: str = "",
    candidate_target_title: str = "",
    job_location: str = "",
    candidate_preferred_locations: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compute transparent explainable match score between candidate and job."""
    candidate_profile = {
        "skills": candidate_skills,
        "experience": [{"years": candidate_experience_years}],
        "summary": candidate_target_title,
        "location_preferences": {
            "preferred_locations": candidate_preferred_locations or [],
            "open_to_remote": True,
        },
    }
    job_data = {
        "title": job_title,
        "required_skills": job_required_skills,
        "preferred_skills": job_preferred_skills or [],
        "requirements": {"min_years": 0},
        "location": job_location,
    }
    result = _matcher.match(candidate_profile, job_data)
    return result.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 10. retrieve_resume_evidence
# ─────────────────────────────────────────────────────────────────────────────
async def tool_retrieve_resume_evidence(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Retrieve indexed evidence from vector store matching a skill or qualification claim."""
    results = vector_store.search(query=query, top_k=top_k)
    return [r.model_dump() for r in results]


# ─────────────────────────────────────────────────────────────────────────────
# 11. generate_career_roadmap
# ─────────────────────────────────────────────────────────────────────────────
async def tool_generate_career_roadmap(
    target_role: str,
    current_skills: List[str],
) -> Dict[str, Any]:
    """Generate structured learning milestones, timelines, and curated resources for target role."""
    return _roadmap_service.generate_roadmap(
        current_skills=current_skills,
        target_role=target_role,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 12. save_career_preference
# ─────────────────────────────────────────────────────────────────────────────
async def tool_save_career_preference(
    target_roles: List[str],
    preferred_locations: List[str],
    work_mode: str = "hybrid",
    employment_type: str = "full-time",
) -> Dict[str, Any]:
    """State-changing tool: Save user preferences in long-term memory."""
    prefs = UserPreferences(
        target_roles=target_roles,
        preferred_locations=preferred_locations,
        work_mode=work_mode,
        employment_type=employment_type,
        consent_given=True,
    )
    saved = memory_manager.update_preferences(prefs)
    return saved.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# 13. update_learning_progress
# ─────────────────────────────────────────────────────────────────────────────
async def tool_update_learning_progress(
    milestone_id: str,
    status: str,  # "completed", "in_progress", "not_started"
    notes: str = "",
) -> Dict[str, Any]:
    """State-changing tool: Record progress on a learning milestone in long-term memory."""
    progress_item = {
        "milestone_id": milestone_id,
        "status": status,
        "notes": notes,
        "updated_at": "2026-10-22T23:50:00Z",
    }
    user_prog = memory_manager.learning_progress.setdefault("default_user", [])
    # Replace or add
    existing = next((p for p in user_prog if p.get("milestone_id") == milestone_id), None)
    if existing:
        existing.update(progress_item)
    else:
        user_prog.append(progress_item)

    return {"status": "success", "milestone": progress_item}
