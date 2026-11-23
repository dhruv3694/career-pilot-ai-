"""
Gemini LLM Provider - Google Gemini API.
Tier 3: Optional proprietary provider adapter.
"""

import time
import logging
from typing import List, Optional
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider adapter (Proprietary)."""

    def __init__(self, model_name: str = "gemini-1.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name=model_name, api_key=api_key)
        if GEMINI_AVAILABLE and self.api_key:
            genai.configure(api_key=self.api_key)

    async def is_available(self) -> bool:
        return bool(GEMINI_AVAILABLE and self.api_key and self.is_healthy)

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.2,
        max_tokens: int = 1500,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        if not await self.is_available():
            raise RuntimeError("Gemini provider is not available or API key is not configured.")

        start_time = time.perf_counter()
        try:
            model = genai.GenerativeModel(self.model_name)
            # Combine messages into Gemini prompt/history
            system_instruction = "\n".join([m.content for m in messages if m.role == "system"])
            user_content = "\n\n".join([f"{m.role.upper()}: {m.content}" for m in messages if m.role != "system"])

            full_prompt = f"{system_instruction}\n\n{user_content}" if system_instruction else user_content

            generation_config = {
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
            if response_format == "json":
                generation_config["response_mime_type"] = "application/json"

            # Execute generation in async thread
            import asyncio
            response = await asyncio.wait_for(model.generate_content_async(
                full_prompt,
                generation_config=generation_config,
            ), timeout=15.0)
            latency_ms = (time.perf_counter() - start_time) * 1000
            content = response.text if hasattr(response, "text") else ""

            self.record_success()
            return LLMResponse(
                content=content,
                provider_name="gemini",
                model_name=self.model_name,
                is_proprietary=True,  # Clearly identified as proprietary
                is_fallback=False,
                tokens_used=len(content.split()),  # approximate token count
                latency_ms=round(latency_ms, 2),
                status="success",
            )
        except Exception as e:
            self.record_failure()
            logger.error("Gemini generation failed: %s", str(e))
            raise

