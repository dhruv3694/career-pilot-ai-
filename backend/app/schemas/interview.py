"""
Pydantic v2 schemas for interview practice operations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class InterviewStartRequest(BaseModel):
    """Request to start a new interview practice session."""

    candidate_id: str
    job_id: Optional[str] = None
    session_type: str = Field(
        ...,
        description="Type of interview: behavioral, technical, system_design, hr, mixed",
    )


class InterviewQuestion(BaseModel):
    """A single interview question."""

    question_id: str = Field(default="", description="Auto-assigned question identifier")
    question: str
    category: str = Field(description="e.g. behavioral, technical, problem_solving")
    difficulty: str = Field(default="medium", description="easy, medium, hard")
    expected_topics: List[str] = Field(
        default_factory=list,
        description="Key topics the answer should cover",
    )


class InterviewResponse(BaseModel):
    """Candidate's response to an interview question."""

    question_id: str
    answer: str = Field(..., min_length=1)


class InterviewEvaluation(BaseModel):
    """Evaluation of a single interview response."""

    question_id: str
    score: float = Field(ge=0.0, le=10.0)
    feedback: str
    strengths: List[str] = Field(default_factory=list)
    improvements: List[str] = Field(default_factory=list)


class InterviewSessionSchema(BaseModel):
    """Full interview session schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    job_id: Optional[str] = None
    session_type: str
    questions: Optional[List[Dict[str, Any]]] = None
    responses: Optional[List[Dict[str, Any]]] = None
    evaluations: Optional[List[Dict[str, Any]]] = None
    overall_score: Optional[float] = None
    feedback: Optional[str] = None
    created_at: datetime
