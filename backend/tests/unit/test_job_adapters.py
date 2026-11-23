"""
Unit tests for Greenhouse, Lever, and SearXNG job discovery adapters.
All network endpoints are mocked using httpx.Response to avoid external calls and quota consumption.
"""

import pytest
from unittest.mock import AsyncMock, patch
import httpx
from app.services.jobs.greenhouse import GreenhouseAdapter
from app.services.jobs.lever import LeverAdapter
from app.services.jobs.discovery import JobDiscoveryService
from app.services.jobs.schemas import JobListing


@pytest.mark.asyncio
async def test_greenhouse_adapter_parsing():
    adapter = GreenhouseAdapter()
    mock_gh_response = {
        "jobs": [
            {
                "id": 12345,
                "title": "Junior Python Engineer",
                "location": {"name": "Remote"},
                "absolute_url": "https://boards.greenhouse.io/canonical/jobs/12345",
                "content": "Work with Python, Linux, and REST APIs.",
                "updated_at": "2026-10-20T10:00:00Z",
            }
        ]
    }

    mock_resp = httpx.Response(
        200,
        json=mock_gh_response,
        request=httpx.Request("GET", "https://boards-api.greenhouse.io/v1/boards/canonical/jobs?content=true"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        jobs = await adapter.search(board_token="canonical", query="python")
        assert len(jobs) == 1
        assert jobs[0].title == "Junior Python Engineer"
        assert jobs[0].company == "canonical"
        assert jobs[0].source == "greenhouse"
    await adapter.close()


@pytest.mark.asyncio
async def test_lever_adapter_parsing():
    adapter = LeverAdapter()
    mock_lever_response = [
        {
            "id": "lev-987",
            "text": "Full Stack Associate",
            "categories": {"location": "Bangalore", "commitment": "Full-time"},
            "hostedUrl": "https://jobs.lever.co/postman/lev-987",
            "descriptionPlain": "Build TypeScript and React apps.",
            "createdAt": 1729000000000,
        }
    ]

    mock_resp = httpx.Response(
        200,
        json=mock_lever_response,
        request=httpx.Request("GET", "https://api.lever.co/v0/postings/postman?mode=json"),
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp

        jobs = await adapter.search(company="postman", query="stack")
        assert len(jobs) == 1
        assert jobs[0].title == "Full Stack Associate"
        assert jobs[0].location == "Bangalore"
    await adapter.close()


@pytest.mark.asyncio
async def test_job_discovery_deduplication():
    discovery = JobDiscoveryService()
    j1 = JobListing(id="j1", title="Software Engineer", company="Canonical", url="https://u1", description="desc 1")
    j2 = JobListing(id="j2", title="Software Engineer", company="canonical", url="https://u2", description="desc 2")
    j3 = JobListing(id="j3", title="Data Analyst", company="Razorpay", url="https://u3", description="desc 3")

    deduped = discovery._deduplicate([j1, j2, j3])
    assert len(deduped) == 2
    assert deduped[0].title == "Software Engineer"
    assert deduped[1].title == "Data Analyst"
    await discovery.close()
