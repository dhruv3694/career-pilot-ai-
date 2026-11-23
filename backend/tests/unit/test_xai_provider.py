from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.core.config import settings
from app.llm.base import LLMMessage, LLMResponse
from app.llm.manager import LLMManager
from app.llm.xai_provider import XAIProvider


@pytest.mark.asyncio
async def test_xai_provider_uses_responses_api_and_disables_storage():
    provider = XAIProvider(model_name="grok-4.7", api_key="test-key")
    mock_response = httpx.Response(
        200,
        json={
            "output": [
                {
                    "type": "message",
                    "content": [{"type": "output_text", "text": '{"ok": true}'}],
                }
            ],
            "usage": {"total_tokens": 12},
        },
        request=httpx.Request("POST", "https://api.x.ai/v1/responses"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response) as post:
        result = await provider.generate(
            [LLMMessage(role="user", content="Return a JSON object.")],
            response_format="json",
        )

    payload = post.call_args.kwargs["json"]
    assert post.call_args.args[0] == "https://api.x.ai/v1/responses"
    assert payload["model"] == "grok-4.7"
    assert payload["store"] is False
    assert payload["text"]["format"]["type"] == "json_object"
    assert result.content == '{"ok": true}'
    assert result.provider_name == "xai"
    assert result.is_proprietary is True
    assert result.tokens_used == 12


@pytest.mark.asyncio
async def test_xai_provider_records_http_failure():
    provider = XAIProvider(model_name="grok-4.7", api_key="test-key")
    mock_response = httpx.Response(
        503,
        json={"error": "temporarily unavailable"},
        request=httpx.Request("POST", "https://api.x.ai/v1/responses"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        with pytest.raises(httpx.HTTPStatusError):
            await provider.generate([LLMMessage(role="user", content="Test")])

    assert provider.failure_count == 1


@pytest.mark.asyncio
async def test_manager_uses_xai_after_gemini_failure(monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER_PRIORITY", "gemini,xai,groq")
    manager = LLMManager()
    gemini = AsyncMock()
    gemini.is_available.return_value = True
    gemini.generate.side_effect = RuntimeError("Gemini unavailable")
    xai = AsyncMock()
    xai.is_available.return_value = True
    xai.generate.return_value = LLMResponse(
        content="Grok response",
        provider_name="xai",
        model_name="grok-4.7",
    )
    groq = AsyncMock()
    groq.is_available.return_value = True
    manager.providers = {"gemini": gemini, "xai": xai, "groq": groq}

    result = await manager.generate("Hello")

    assert result.provider_name == "xai"
    gemini.generate.assert_awaited_once()
    xai.generate.assert_awaited_once()
    groq.generate.assert_not_awaited()
