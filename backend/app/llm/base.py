"""
LLM Provider Base Interface for CareerPilot AI.
Supports open-weight hosted models (Tier 2), optional proprietary adapters (Tier 3),
and deterministic local fallback (Tier 1).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    """Chat message structure."""
    role: str = Field(..., description="'system', 'user', or 'assistant'")
    content: str


class LLMResponse(BaseModel):
    """Unified response object from any LLM provider."""
    content: str
    provider_name: str
    model_name: str
    is_proprietary: bool = False
    is_fallback: bool = False
    tokens_used: int = 0
    latency_ms: float = 0.0
    status: str = "success"  # success, error, fallback
    raw_response: Optional[Dict[str, Any]] = None

    @property
    def provider(self) -> str:
        return self.provider_name


class BaseLLMProvider(ABC):
    """Abstract base class for all LLM providers."""

    def __init__(self, model_name: str, api_key: Optional[str] = None):
        self.model_name = model_name
        self.api_key = api_key
        self.is_healthy: bool = True
        self.failure_count: int = 0
        self.max_failures: int = 3

    @abstractmethod
    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        """Generate a response from the model."""
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider is configured and reachable."""
        pass

    def record_success(self):
        self.is_healthy = True
        self.failure_count = 0

    def record_failure(self):
        self.failure_count += 1
        if self.failure_count >= self.max_failures:
            self.is_healthy = False
