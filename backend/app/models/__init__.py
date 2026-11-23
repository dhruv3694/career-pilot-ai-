"""
Import all ORM models so that ``Base.metadata`` is fully populated
when ``init_db()`` is called.
"""

from app.models.models import (
    AgentExecution,
    AgentMessage,
    ApprovalRequest,
    CandidateProfile,
    CareerEvent,
    CareerPreference,
    EventSource,
    InterviewSession,
    JobListing,
    JobMatch,
    JobSource,
    LearningMilestone,
    LearningPlan,
    MemoryEntry,
    ProviderExecution,
    ResumeAssessment,
    ResumeDocument,
    ResumeEvidence,
    SkillAssessment,
    ToolExecution,
    WorkflowRun,
)

__all__ = [
    "AgentExecution",
    "AgentMessage",
    "ApprovalRequest",
    "CandidateProfile",
    "CareerEvent",
    "CareerPreference",
    "EventSource",
    "InterviewSession",
    "JobListing",
    "JobMatch",
    "JobSource",
    "LearningMilestone",
    "LearningPlan",
    "MemoryEntry",
    "ProviderExecution",
    "ResumeAssessment",
    "ResumeDocument",
    "ResumeEvidence",
    "SkillAssessment",
    "ToolExecution",
    "WorkflowRun",
]
