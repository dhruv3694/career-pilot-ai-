"""
Pydantic v2 schemas for memory, preferences, and consent operations.
"""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class MemoryEntrySchema(BaseModel):
    """Full schema for a memory entry."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    candidate_id: str
    memory_type: str
    key: str
    value: Optional[Any] = None
    source: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    expires_at: Optional[datetime] = None


class MemoryCreateRequest(BaseModel):
    """Request to create a new memory entry."""

    candidate_id: str
    memory_type: str = Field(
        ...,
        description="Type of memory: preference, context, interaction, fact",
    )
    key: str = Field(..., min_length=1, max_length=255)
    value: Optional[Any] = None
    source: Optional[str] = Field(
        default=None,
        description="Origin of the memory: resume, conversation, agent, user",
    )
    expires_at: Optional[datetime] = None


class MemoryUpdateRequest(BaseModel):
    """Request to update an existing memory entry."""

    value: Optional[Any] = None
    source: Optional[str] = None
    expires_at: Optional[datetime] = None


class PreferenceSchema(BaseModel):
    """Schema for a user preference (wraps a memory entry of type 'preference')."""

    model_config = ConfigDict(from_attributes=True)

    key: str
    value: Any
    source: Optional[str] = None
    updated_at: datetime


class ConsentRequest(BaseModel):
    """Request for user consent on a data-processing action."""

    candidate_id: str
    action: str = Field(
        ...,
        description="The action requiring consent, e.g. 'store_resume_data', 'share_with_employer'",
    )
    scope: str = Field(
        ...,
        description="Scope of the consent: 'session', 'persistent', 'one_time'",
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional details about what the consent covers",
    )
    granted: bool = Field(
        ...,
        description="Whether consent is granted",
    )
