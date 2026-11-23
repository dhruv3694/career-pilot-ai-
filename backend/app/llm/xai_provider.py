"""xAI Grok provider using the Responses API."""

import logging
import time
from typing import List, Optional

import httpx

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

_RESPONSES_URL = "https://api.x.ai/v1/responses"
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)


class XAIProvider(BaseLLMProvider):
    """xAI hosted Grok adapter."""

    is_proprietary = True

    async def is_available(self) -> bool:
        return bool(self.api_key and self.is_healthy)

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        if not await self.is_available():
            raise RuntimeError("xAI provider is not available or API key is not configured.")

        payload: dict = {
            "model": self.model_name,
            "input": [{"role": message.role, "content": message.content} for message in messages],
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "store": False,
        }
        if response_format == "json":
            payload["text"] = {"format": {"type": "json_object"}}

        start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                response = await client.post(
                    _RESPONSES_URL,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()

            data = response.json()
            content = data.get("output_text", "")
            if not content:
                text_parts = [
                    part["text"]
                    for item in data.get("output", [])
                    if item.get("type") == "message"
                    for part in item.get("content", [])
                    if part.get("type") == "output_text" and isinstance(part.get("text"), str)
                ]
                content = "\n".join(text_parts)
            if not content:
                raise RuntimeError("xAI response did not contain generated text.")

            usage = data.get("usage") or {}
            tokens_used = usage.get("total_tokens")
            if tokens_used is None:
                tokens_used = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)

            self.record_success()
            return LLMResponse(
                content=content,
                provider_name="xai",
                model_name=self.model_name,
                is_proprietary=True,
                is_fallback=False,
                tokens_used=tokens_used,
                latency_ms=round((time.perf_counter() - start_time) * 1000, 2),
                status="success",
            )
        except Exception as exc:
            self.record_failure()
            logger.error("xAI Grok generation failed: %s", exc)
            raise
