"""
Unit tests for Centralized LLM Provider Architecture, Graceful Fallback, and Memory & Privacy.
"""

import pytest
from app.llm.fallback import DeterministicFallbackProvider
from app.llm.base import LLMMessage
from app.llm.manager import LLMManager
from app.memory.memory_manager import MemoryManager, UserPreferences
from app.memory.vector_store import LocalEvidenceVectorStore


@pytest.mark.asyncio
async def test_deterministic_fallback_provider():
    provider = DeterministicFallbackProvider()
    assert await provider.is_available() is True

    messages = [LLMMessage(role="user", content="Review my resume bullets")]
    response = await provider.generate(messages, response_format="json")

    assert response.is_fallback is True
    assert response.is_proprietary is False
    assert response.provider_name == "deterministic_fallback"
    assert "deterministic" in response.content.lower()


@pytest.mark.asyncio
async def test_llm_manager_fallback_chain_when_no_keys():
    manager = LLMManager()
    # Force fallback
    response = await manager.generate(
        messages=[LLMMessage(role="user", content="Give interview feedback")],
        response_format="json",
    )
    assert response.status in ("success", "fallback")
    assert response.is_fallback is True


def test_memory_and_privacy_controls():
    mem = MemoryManager()
    user_id = "test_student"

    # Default preferences
    prefs = mem.get_preferences(user_id)
    assert prefs.consent_given is True

    # Save job
    saved = mem.save_job({"id": "job_1", "title": "SE"}, user_id)
    assert saved is True
    assert len(mem.get_saved_jobs(user_id)) == 1

    # Right to be forgotten (purge)
    purge_report = mem.purge_user_data(user_id)
    assert purge_report["deleted_jobs"] == 1
    assert len(mem.get_saved_jobs(user_id)) == 0


def test_local_vector_evidence_store():
    store = LocalEvidenceVectorStore()
    store.index_document(
        doc_id="doc1",
        doc_type="resume",
        title="Resume 1",
        text="Proficient in Kubernetes container orchestration and Docker swarm deployment.",
    )
    results = store.search("Kubernetes container orchestration", top_k=1)
    assert len(results) == 1
    assert results[0].doc_id == "doc1"
    assert results[0].score > 0.1

