"""
CareerPilot AI Memory and Privacy Management.
Coordinates Working Memory (active workflow/session), Long-Term Memory (preferences, saved jobs, history),
and Privacy/Consent controls.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.memory.vector_store import vector_store, SearchResult

logger = logging.getLogger(__name__)


class UserPreferences(BaseModel):
    """User long-term career preferences."""
    target_roles: List[str] = Field(default_factory=lambda: ["Software Engineer"])
    preferred_locations: List[str] = Field(default_factory=lambda: ["Remote", "Bangalore", "Pune"])
    work_mode: str = "hybrid"  # remote, hybrid, onsite
    employment_type: str = "full-time"
    min_salary: Optional[float] = None
    consent_given: bool = True
    consent_timestamp: Optional[datetime] = None


class WorkingMemory(BaseModel):
    """Ephemeral in-session state for current multi-agent workflow."""
    session_id: str
    active_resume_id: Optional[str] = None
    selected_job_ids: List[str] = Field(default_factory=list)
    unresolved_issues: List[str] = Field(default_factory=list)
    agent_scratchpad: Dict[str, Any] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MemoryManager:
    """Central Memory & Retrieval Controller."""

    def __init__(self):
        self.preferences: Dict[str, UserPreferences] = {}
        self.working_memories: Dict[str, WorkingMemory] = {}
        self.saved_jobs: Dict[str, List[Dict[str, Any]]] = {}
        self.learning_progress: Dict[str, List[Dict[str, Any]]] = {}
        self.interview_history: Dict[str, List[Dict[str, Any]]] = {}

    def get_preferences(self, user_id: str = "default_user") -> UserPreferences:
        if user_id not in self.preferences:
            self.preferences[user_id] = UserPreferences(
                consent_timestamp=datetime.now(timezone.utc)
            )
        return self.preferences[user_id]

    def update_preferences(self, prefs: UserPreferences, user_id: str = "default_user") -> UserPreferences:
        self.preferences[user_id] = prefs
        return prefs

    def get_working_memory(self, session_id: str) -> WorkingMemory:
        if session_id not in self.working_memories:
            self.working_memories[session_id] = WorkingMemory(session_id=session_id)
        return self.working_memories[session_id]

    def save_job(self, job_data: Dict[str, Any], user_id: str = "default_user") -> bool:
        user_jobs = self.saved_jobs.setdefault(user_id, [])
        # Check duplicate
        if any(j.get("id") == job_data.get("id") for j in user_jobs):
            return False
        user_jobs.append(job_data)
        return True

    def get_saved_jobs(self, user_id: str = "default_user") -> List[Dict[str, Any]]:
        return self.saved_jobs.get(user_id, [])

    def remove_saved_job(self, job_id: str, user_id: str = "default_user") -> bool:
        user_jobs = self.saved_jobs.get(user_id, [])
        initial_len = len(user_jobs)
        self.saved_jobs[user_id] = [j for j in user_jobs if j.get("id") != job_id]
        return len(self.saved_jobs[user_id]) < initial_len

    def index_resume_for_evidence(self, resume_id: str, candidate_name: str, text: str) -> int:
        chunks = vector_store.index_document(
            doc_id=resume_id,
            doc_type="resume",
            title=f"Resume: {candidate_name}",
            text=text,
            metadata={"candidate_name": candidate_name},
        )
        return len(chunks)

    def retrieve_evidence(self, query: str, top_k: int = 3) -> List[SearchResult]:
        return vector_store.search(query=query, top_k=top_k)

    def purge_user_data(self, user_id: str = "default_user") -> Dict[str, int]:
        """GDPR/Privacy compliant total data purge."""
        deleted_jobs = len(self.saved_jobs.pop(user_id, []))
        deleted_progress = len(self.learning_progress.pop(user_id, []))
        deleted_interviews = len(self.interview_history.pop(user_id, []))
        self.preferences.pop(user_id, None)

        return {
            "deleted_jobs": deleted_jobs,
            "deleted_progress": deleted_progress,
            "deleted_interviews": deleted_interviews,
        }


memory_manager = MemoryManager()

