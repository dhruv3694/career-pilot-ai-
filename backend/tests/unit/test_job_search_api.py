from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.api.routes import jobs as jobs_module
from app.services.jobs.schemas import JobListing, JobSearchResponse


@pytest.mark.asyncio
async def test_search_returns_only_public_source_results(monkeypatch):
    listing = JobListing(
        id="123",
        title="Python Backend Engineer",
        company="canonical",
        location="Remote",
        description="Build Python services.",
        url="https://boards.greenhouse.io/canonical/jobs/123",
        source="greenhouse",
    )
    service_response = JobSearchResponse(
        jobs=[listing],
        total_results=1,
        sources_searched=["greenhouse", "lever"],
        search_query="python backend",
    )
    discover = AsyncMock(return_value=service_response)
    monkeypatch.setattr(jobs_module.job_discovery_service, "discover", discover)

    result = await jobs_module.search_jobs(
        query="python backend",
        location=None,
        work_mode=None,
        experience_level=None,
        source="all",
    )

    assert result["status"] == "success"
    assert result["total_results"] == 1
    assert result["sources_searched"] == ["greenhouse", "lever"]
    assert result["jobs"][0]["id"] == "greenhouse:123"
    assert result["jobs"][0]["verification_status"] == "public_listing_found"
    assert result["jobs"][0]["original_url"] == listing.url
    assert result["jobs"][0]["retrieved_at"] == result["retrieved_at"]
    assert result["jobs"][0]["is_demo_data"] is False
    discover.assert_awaited_once()


@pytest.mark.asyncio
async def test_web_search_reports_unconfigured_source_without_calling_discovery(monkeypatch):
    discover = AsyncMock()
    monkeypatch.setattr(jobs_module.job_discovery_service, "discover", discover)
    monkeypatch.setattr(jobs_module.settings, "SEARXNG_ENABLED", False)

    result = await jobs_module.search_jobs(
        query="python backend",
        location=None,
        work_mode=None,
        experience_level=None,
        source="web",
    )

    assert result["status"] == "unavailable"
    assert result["jobs"] == []
    assert "not configured" in result["errors"][0]
    discover.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_reports_partial_source_failures(monkeypatch):
    listing = JobListing(
        id="456",
        title="Backend Developer",
        company="canonical",
        url="https://boards.greenhouse.io/canonical/jobs/456",
        source="greenhouse",
    )
    response = JobSearchResponse(
        jobs=[listing],
        total_results=1,
        sources_searched=["greenhouse", "lever"],
        errors=["Lever company netflix failed: service unavailable"],
    )
    monkeypatch.setattr(
        jobs_module.job_discovery_service,
        "discover",
        AsyncMock(return_value=response),
    )

    result = await jobs_module.search_jobs(
        query="backend developer",
        location=None,
        work_mode=None,
        experience_level=None,
        source="all",
    )

    assert result["status"] == "partial_success"
    assert result["total_results"] == 1
    assert result["errors"] == response.errors


def test_post_search_validates_filters_like_get(monkeypatch):
    async def skip_database_init():
        return None

    monkeypatch.setattr(main, "init_db", skip_database_init)
    discover = AsyncMock(
        return_value=JobSearchResponse(jobs=[], total_results=0, search_query="valid query")
    )
    monkeypatch.setattr(jobs_module.job_discovery_service, "discover", discover)

    with TestClient(main.app) as client:
        invalid_payloads = [
            {"query": "x", "source": "web"},
            {"query": "valid query", "work_mode": "remote-ish", "source": "web"},
            {"query": "valid query", "source": "unknown"},
            {"query": "x" * 121, "source": "web"},
        ]
        for payload in invalid_payloads:
            response = client.post("/api/jobs/search", json=payload)
            assert response.status_code == 422

    discover.assert_not_awaited()
