"""
Pydantic v2 schemas for career roadmap and learning plan operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LearningMilestoneSchema(BaseModel):
    """Schema for a single learning milestone."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    plan_id: str
    title: str
    description: Optional[str] = None
    skill_area: Optional[str] = None
    resources: Optional[List[Dict[str, Any]]] = None
    is_completed: bool = False
    target_date: Optional[datetime] = None
    completed_date: Optional[datetime] = None
    created_at: datetime


class SkillGapAnalysis(BaseModel):
    """Analysis of a single skill gap."""

    skill: str
    current_level: str = Field(description="beginner, intermediate, advanced, expert, none")
    required_level: str = Field(description="beginner, intermediate, advanced, expert")
    gap: str = Field(description="Description of the skill gap")
    resources: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Recommended learning resources with title, url, type, estimated_hours",
    )


class CareerRoadmapRequest(BaseModel):
    """Request to generate a career roadmap."""

    candidate_id: str
    target_role: str = Field(..., min_length=1, max_length=255)


class CareerRoadmapResponse(BaseModel):
    """Response containing a generated career roadmap."""

    model_config = ConfigDict(from_attributes=True)

    plan_id: str
    candidate_id: str
    target_role: str
    current_skills: Optional[List[str]] = None
    target_skills: Optional[List[str]] = None
    skill_gaps: List[SkillGapAnalysis]
    milestones: List[LearningMilestoneSchema]
    timeline_weeks: Optional[int] = None
    status: str
    summary: Optional[str] = None
    created_at: datetime
