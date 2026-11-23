"""
Pydantic v2 schemas for agent orchestration and workflow monitoring.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class AgentStatus(BaseModel):
    """Current status of a single agent."""

    agent_name: str
    status: str = Field(description="idle, running, completed, failed, waiting")
    last_action: Optional[str] = None
    current_task: Optional[str] = None


class WorkflowStatus(BaseModel):
    """Status of a running workflow."""

    model_config = ConfigDict(from_attributes=True)

    workflow_id: str
    workflow_type: str
    status: str
    agents: List[AgentStatus] = Field(default_factory=list)
    messages: List["AgentMessageSchema"] = Field(default_factory=list)
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0, description="Progress percentage")
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class AgentMessageSchema(BaseModel):
    """Schema for inter-agent messages."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    workflow_id: str
    from_agent: str
    to_agent: str
    message_type: str
    content: Optional[Dict[str, Any]] = None
    created_at: datetime


class ToolExecutionSchema(BaseModel):
    """Schema for tool execution records."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_execution_id: str
    tool_name: str
    input_params: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    execution_time_ms: Optional[int] = None
    created_at: datetime


class DemonstrationStep(BaseModel):
    """A single step in a demonstration scenario."""

    step_number: int
    description: str
    agent: Optional[str] = None
    tool: Optional[str] = None
    status: str = Field(default="pending", description="pending, running, completed, failed")
    result: Optional[Dict[str, Any]] = None


class DemonstrationScenario(BaseModel):
    """A demonstration scenario showcasing agent capabilities."""

    scenario_id: str
    name: str
    description: str
    status: str = Field(default="pending", description="pending, running, completed, failed")
    steps: List[DemonstrationStep] = Field(default_factory=list)
    results: Optional[Dict[str, Any]] = None
