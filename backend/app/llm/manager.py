"""
Central LLM Manager for CareerPilot AI.
Coordinates provider selection, fallback logic, rate limits, and budget tracking.
Prioritizes Open-Weight models (Groq) -> Optional Proprietary (Gemini) -> Deterministic Fallback.
"""

import logging
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse
from app.llm.groq_provider import GroqProvider
from app.llm.gemini_provider import GeminiProvider
from app.llm.xai_provider import XAIProvider
from app.llm.fallback import DeterministicFallbackProvider

logger = logging.getLogger(__name__)


class LLMManager:
    """Manages multi-tier LLM providers with automatic graceful degradation."""

    def __init__(self):
        self.providers: Dict[str, BaseLLMProvider] = {}
        self.fallback_provider = DeterministicFallbackProvider()
        
        # Initialize Groq (Tier 2 Open-Weight)
        self.providers["groq"] = GroqProvider(
            model_name=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
        )

        # Initialize Gemini (Tier 3 Optional Proprietary)
        self.providers["gemini"] = GeminiProvider(
            model_name=settings.GEMINI_MODEL,
            api_key=settings.GEMINI_API_KEY,
        )

        self.providers["xai"] = XAIProvider(
            model_name=settings.GROK_MODEL,
            api_key=settings.XAI_API_KEY,
        )

        # Execution stats tracking
        self.total_requests: int = 0
        self.successful_requests: int = 0
        self.fallback_requests: int = 0
        self.total_tokens_consumed: int = 0
        self.provider_history: List[Dict] = []

    def get_configured_providers(self) -> List[str]:
        return settings.llm_provider_priority_list

    async def get_provider_status(self) -> Dict[str, dict]:
        """Return health and availability status of all registered providers."""
        status = {}
        for name, provider in self.providers.items():
            available = await provider.is_available()
            status[name] = {
                "available": available,
                "healthy": provider.is_healthy,
                "model": provider.model_name,
                "is_proprietary": getattr(provider, "is_proprietary", False) or (name == "gemini"),
                "failures": provider.failure_count,
            }
        status["deterministic_fallback"] = {
            "available": True,
            "healthy": True,
            "model": "deterministic-rule-engine-v1",
            "is_proprietary": False,
            "failures": 0,
        }
        return status

    def is_available(self) -> bool:
        """Return True if any provider (including deterministic fallback) is available."""
        return True

    async def generate(
        self,
        prompt_or_messages: Any = None,
        messages: Optional[List[LLMMessage]] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: Optional[str] = None,
        force_provider: Optional[str] = None,
    ) -> LLMResponse:
        """
        Execute generation following configured provider priority.
        If all external providers fail or none are configured, seamlessly uses Deterministic Fallback.
        Accepts either a single string prompt or a list of LLMMessage objects.
        """
        if isinstance(prompt_or_messages, str):
            messages = [LLMMessage(role="user", content=prompt_or_messages)]
        elif isinstance(prompt_or_messages, list):
            messages = prompt_or_messages
        elif messages is None:
            messages = [LLMMessage(role="user", content="Hello")]
        self.total_requests += 1
        priority = [force_provider] if force_provider else self.get_configured_providers()

        for provider_name in priority:
            if provider_name in self.providers:
                provider = self.providers[provider_name]
                if await provider.is_available():
                    try:
                        logger.info("Attempting generation with provider: %s", provider_name)
                        response = await provider.generate(
                            messages=messages,
                            temperature=temperature,
                            max_tokens=max_tokens,
                            response_format=response_format,
                        )
                        self.successful_requests += 1
                        self.total_tokens_consumed += response.tokens_used
                        self._record_history(provider_name, response.status, response.latency_ms)
                        return response
                    except Exception as exc:
                        logger.warning("Provider %s failed: %s. Continuing fallback chain...", provider_name, str(exc))
                        self._record_history(provider_name, "failed", 0, str(exc))
                        continue

        # If we reached here, use Deterministic Fallback
        logger.info("Using Deterministic Fallback Engine (No external LLM available).")
        self.fallback_requests += 1
        response = await self.fallback_provider.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        self._record_history("deterministic_fallback", "fallback", response.latency_ms)
        return response

    def _record_history(self, provider: str, status: str, latency: float, error: str = ""):
        self.provider_history.append({
            "provider": provider,
            "status": status,
            "latency_ms": latency,
            "error": error,
        })
        if len(self.provider_history) > 100:
            self.provider_history.pop(0)


# Global singleton instance
llm_manager = LLMManager()
