"""
Integration tests for Jury Examination Failure Demonstration Scenarios A through F.
"""

import pytest
from app.api.routes.demonstrations import (
    run_scenario_a,
    run_scenario_b,
    run_scenario_c,
    run_scenario_d,
    run_scenario_e,
    run_scenario_f,
)


@pytest.mark.asyncio
async def test_scenario_a_disagreement_resolution():
    res = await run_scenario_a()
    assert res["conflict_resolved"] is True
    assert "Docker" in res["evidence_retrieved"]["snippet"]


@pytest.mark.asyncio
async def test_scenario_b_unavailable_job_recovery():
    res = await run_scenario_b()
    assert res["check_result"]["availability"] == "unavailable"
    assert len(res["recovery_actions"]) >= 3
    assert res["replacement_job"]["verification_status"] == "live_verified"


@pytest.mark.asyncio
async def test_scenario_c_search_failure_partial_results():
    res = await run_scenario_c()
    assert res["results_status"] == "partial_success"
    assert len(res["failed_sources"]) == 1
    assert "searxng_metasearch" in res["failed_sources"][0]["source"]


@pytest.mark.asyncio
async def test_scenario_d_deterministic_fallback():
    res = await run_scenario_d()
    assert res["is_fallback"] is True
    assert len(res["guaranteed_offline_features"]) >= 4


@pytest.mark.asyncio
async def test_scenario_e_conflicting_job_info():
    res = await run_scenario_e()
    assert res["conflict_detected"] is True
    assert res["resolved_values"]["selected_deadline"] == "2026-11-30"


@pytest.mark.asyncio
async def test_scenario_f_prompt_injection_neutralization():
    res = await run_scenario_f()
    assert res["injection_detected"] is True
    assert "[FILTERED_UNTRUSTED_INSTRUCTION]" in res["sanitized_text"]

