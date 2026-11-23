"""
Career Planning and Learning Roadmap Router.
Generates structured milestone plans, estimated timelines, and free resources
to bridge candidate skill gaps.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.career.roadmap import CareerRoadmapService
from app.memory.memory_manager import memory_manager

router = APIRouter(prefix="/career", tags=["Career Roadmap"])
roadmap_service = CareerRoadmapService()


class RoadmapRequest(BaseModel):
    target_role: str = "Software Engineer"
    current_skills: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)


class UpdateMilestoneRequest(BaseModel):
    milestone_id: str
    status: str  # completed, in_progress, not_started
    notes: Optional[str] = ""


@router.post("/roadmap")
async def generate_career_roadmap(payload: RoadmapRequest):
    """Generate structured learning milestones for a target career transition."""
    roadmap = roadmap_service.generate_roadmap(
        current_skills=payload.current_skills,
        target_role=payload.target_role,
        skill_gaps=payload.skill_gaps,
    )
    return {
        "status": "success",
        "roadmap": roadmap,
    }


@router.get("/progress")
async def get_learning_progress():
    """Retrieve recorded learning progress and completed milestones."""
    progress = memory_manager.learning_progress.get("default_user", [])
    return {
        "status": "success",
        "progress": progress,
    }


@router.post("/progress/update")
async def update_learning_progress(payload: UpdateMilestoneRequest):
    """Update progress status on a learning milestone."""
    progress_item = {
        "milestone_id": payload.milestone_id,
        "status": payload.status,
        "notes": payload.notes,
        "updated_at": "2026-10-22T23:55:00Z",
    }
    user_prog = memory_manager.learning_progress.setdefault("default_user", [])
    existing = next((p for p in user_prog if p.get("milestone_id") == payload.milestone_id), None)
    if existing:
        existing.update(progress_item)
    else:
        user_prog.append(progress_item)

    return {
        "status": "success",
        "milestone": progress_item,
    }

