"""
Integration tests for the LangGraph multi-agent workflow and Jury Failure Scenarios.
"""

import pytest
from app.agents.workflow import get_workflow, AgentState


@pytest.mark.asyncio
async def test_full_multi_agent_state_graph_execution():
    workflow = get_workflow()

    initial_state: AgentState = {
        "workflow_id": 999,
        "candidate_id": 1,
        "messages": [],
        "resume_id": None,
        "resume_text": (
            "Dhruv Patel\n"
            "Email: dhruv@example.com | Phone: 9876543210\n"
            "Skills: Python, FastAPI, Docker, SQL, React\n"
            "Experience: Backend Developer building scalable APIs."
        ),
        "extracted_profile": None,
        "ats_report": None,
        "resume_evidence": None,
        "llm_review": None,
        "job_query": "Python developer",
        "job_location": "Remote",
        "discovered_jobs": None,
        "selected_jobs": None,
        "job_matches": None,
        "event_query": None,
        "discovered_events": None,
        "target_role": "Backend Engineer",
        "skill_gaps": None,
        "career_roadmap": None,
        "interview_session": None,
        "current_agent": "supervisor",
        "next_agent": None,
        "workflow_status": "starting",
        "errors": [],
        "warnings": [],
        "agent_executions": [],
        "tool_executions": [],
        "start_time": 0.0,
        "failed_sources": [],
        "retry_count": 0,
        "fallback_used": False,
        "pending_approvals": [],
        "provider_used": None,
        "provider_is_proprietary": None,
    }

    result = await workflow.ainvoke(initial_state)

    assert result["workflow_status"] in ("completed", "partial")
    assert result.get("extracted_profile") is not None
    assert result.get("ats_report") is not None
    assert result.get("career_roadmap") is not None
    assert result.get("interview_session") is not None
    assert len(result.get("agent_executions", [])) >= 5

