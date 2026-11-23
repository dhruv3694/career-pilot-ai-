"""
Pydantic v2 schemas for career event operations.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CareerEventSchema(BaseModel):
    """Full career event schema."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    external_id: Optional[str] = None
    name: str
    organizer: Optional[str] = None
    event_date: Optional[datetime] = None
    event_end_date: Optional[datetime] = None
    timezone: Optional[str] = None
    venue: Optional[str] = None
    is_online: bool = False
    eligibility: Optional[str] = None
    target_roles: Optional[List[str]] = None
    registration_deadline: Optional[datetime] = None
    registration_url: Optional[str] = None
    source_url: Optional[str] = None
    retrieval_timestamp: Optional[datetime] = None
    verification_status: str = "pending"
    description: Optional[str] = None
    created_at: datetime


class EventSearchRequest(BaseModel):
    """Request body for searching career events."""

    query: Optional[str] = Field(default=None, max_length=500)
    location: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    is_online: Optional[bool] = None
    target_role: Optional[str] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class EventSearchResponse(BaseModel):
    """Response from an event search query."""

    events: List[CareerEventSchema]
    total: int
    page: int
    page_size: int
    sources_used: List[str]
