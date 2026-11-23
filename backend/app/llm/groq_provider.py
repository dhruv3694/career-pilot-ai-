"""
Groq LLM Provider - Serves Open-Weight Models (e.g. Llama 3.1, Mixtral).
Tier 2 in Open-Source Priority Order.
"""

import time
import logging
from typing import List, Optional
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class GroqProvider(BaseLLMProvider):
    """Groq hosted inference provider for open-weight models."""

    def __init__(self, model_name: str = "llama-3.1-70b-versatile", api_key: Optional[str] = None):
        super().__init__(model_name=model_name, api_key=api_key)
        self.client: Optional[AsyncGroq] = None
        if GROQ_AVAILABLE and self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)

    async def is_available(self) -> bool:
        return bool(GROQ_AVAILABLE and self.api_key and self.is_healthy)

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        if not await self.is_available() or not self.client:
            raise RuntimeError("Groq provider is not available or API key is not configured.")

        start_time = time.perf_counter()
        formatted_messages = [{"role": m.role, "content": m.content} for m in messages]

        kwargs = {
            "model": self.model_name,
            "messages": formatted_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}

        try:
            chat_completion = await self.client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start_time) * 1000
            content = chat_completion.choices[0].message.content or ""
            total_tokens = getattr(chat_completion.usage, "total_tokens", 0) if chat_completion.usage else 0

            self.record_success()
            return LLMResponse(
                content=content,
                provider_name="groq",
                model_name=self.model_name,
                is_proprietary=False,  # Weights are open (Llama / Mixtral)
                is_fallback=False,
                tokens_used=total_tokens,
                latency_ms=round(latency_ms, 2),
                status="success",
            )
        except Exception as e:
            self.record_failure()
            logger.error("Groq generation failed: %s", str(e))
            raise

