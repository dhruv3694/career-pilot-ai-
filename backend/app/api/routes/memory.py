"""
Memory and Privacy API Router.
Manages working memory, long-term memory, career constraints, and user privacy rights (GDPR delete).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.memory.memory_manager import memory_manager, UserPreferences
from app.memory.vector_store import vector_store

router = APIRouter(prefix="/memory", tags=["Memory & Privacy"])


class UpdatePreferencesRequest(BaseModel):
    target_roles: List[str] = Field(default_factory=lambda: ["Software Engineer"])
    preferred_locations: List[str] = Field(default_factory=lambda: ["Remote", "Bangalore", "Pune"])
    work_mode: str = "hybrid"
    employment_type: str = "full-time"
    min_salary: Optional[float] = None
    consent_given: bool = True


@router.get("/preferences")
async def get_preferences():
    """Retrieve long-term preferences and consent status."""
    prefs = memory_manager.get_preferences()
    return prefs.model_dump()


@router.put("/preferences")
async def update_preferences(payload: UpdatePreferencesRequest):
    """Update career preferences and consent settings."""
    prefs = UserPreferences(**payload.model_dump())
    updated = memory_manager.update_preferences(prefs)
    return {
        "status": "success",
        "preferences": updated.model_dump(),
    }


@router.get("/overview")
async def get_memory_overview():
    """Inspect all working and long-term memory partitions."""
    prefs = memory_manager.get_preferences()
    saved_jobs = memory_manager.get_saved_jobs()
    learning = memory_manager.learning_progress.get("default_user", [])
    interviews = memory_manager.interview_history.get("default_user", [])
    vector_chunks_count = len(vector_store.chunks)

    return {
        "preferences": prefs.model_dump(),
        "saved_jobs_count": len(saved_jobs),
        "learning_milestones_count": len(learning),
        "interview_records_count": len(interviews),
        "indexed_evidence_chunks": vector_chunks_count,
        "consent_active": prefs.consent_given,
    }


@router.delete("/purge")
async def purge_all_memory():
    """Execute complete data deletion (GDPR Right to Be Forgotten)."""
    result = memory_manager.purge_user_data()
    return {
        "status": "success",
        "message": "All candidate profile data, preferences, saved jobs, and memory records have been purged.",
        "details": result,
    }

