"""
Multi-Agent Orchestration and Agent Control Center API Router.
Coordinates LangGraph StateGraph execution across the 6 specialized agents + Supervisor.
Maintains authentic backend logs of agent messages, tool executions, and state transitions.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agents.workflow import get_workflow, AgentState
from app.api.routes.resumes import RESUME_STORE

router = APIRouter(prefix="/agents", tags=["Agent Control Center"])
logger = logging.getLogger(__name__)

# Run history store
WORKFLOW_RUNS: Dict[str, Dict[str, Any]] = {}


class TriggerWorkflowRequest(BaseModel):
    resume_id: Optional[str] = None
    resume_text: Optional[str] = None
    target_role: Optional[str] = "Software Engineer"
    job_query: Optional[str] = "software developer entry level"
    job_location: Optional[str] = "Remote"
    candidate_id: Optional[int] = 1


@router.post("/run")
async def run_multi_agent_workflow(payload: TriggerWorkflowRequest):
    """
    Execute the multi-agent career intelligence workflow using LangGraph.
    Runs Resume Intelligence -> Job Discovery -> Career Events -> Job Matching -> Career Planning -> Interview Prep -> Supervisor Validation.
    """
    workflow_id = str(uuid.uuid4())
    
    # Retrieve resume text from store if resume_id provided
    resume_text = payload.resume_text or ""
    if payload.resume_id and payload.resume_id in RESUME_STORE:
        resume_text = RESUME_STORE[payload.resume_id].get("raw_text", "")

    # Initial state
    initial_state: AgentState = {
        "workflow_id": hash(workflow_id) % 100000,
        "candidate_id": payload.candidate_id or 1,
        "messages": [],
        "resume_id": 1 if payload.resume_id else None,
        "resume_text": resume_text,
        "extracted_profile": None,
        "ats_report": None,
        "resume_evidence": None,
        "llm_review": None,
        "job_query": payload.job_query,
        "job_location": payload.job_location,
        "discovered_jobs": None,
        "selected_jobs": None,
        "job_matches": None,
        "event_query": None,
        "discovered_events": None,
        "target_role": payload.target_role,
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
        "start_time": time.time(),
        "failed_sources": [],
        "retry_count": 0,
        "fallback_used": False,
        "pending_approvals": [],
        "provider_used": None,
        "provider_is_proprietary": None,
    }

    workflow = get_workflow()

    try:
        final_state = await workflow.ainvoke(initial_state)
        elapsed_sec = time.time() - (final_state.get("start_time") or time.time())

        # Compile serializable execution record
        run_record = {
            "run_id": workflow_id,
            "status": final_state.get("workflow_status", "completed"),
            "elapsed_seconds": round(elapsed_sec, 2),
            "target_role": payload.target_role,
            "provider_used": final_state.get("provider_used", "deterministic_fallback"),
            "provider_is_proprietary": final_state.get("provider_is_proprietary", False),
            "fallback_used": final_state.get("fallback_used", False),
            "agent_executions": final_state.get("agent_executions", []),
            "tool_calls": [
                call for ex in final_state.get("agent_executions", [])
                for call in ex.get("tool_calls", [])
            ],
            "messages": [
                m if isinstance(m, dict) else {"role": getattr(m, "type", "agent"), "content": str(getattr(m, "content", m))}
                for m in final_state.get("messages", [])
            ],
            "errors": final_state.get("errors", []),
            "warnings": final_state.get("warnings", []),
            "summary": {
                "ats_score": final_state.get("ats_report", {}).get("overall_score") if final_state.get("ats_report") else None,
                "jobs_discovered": len(final_state.get("discovered_jobs") or []),
                "events_discovered": len(final_state.get("discovered_events") or []),
                "matches_computed": len(final_state.get("job_matches") or []),
                "milestones_generated": len(final_state.get("career_roadmap", {}).get("milestones", [])) if final_state.get("career_roadmap") else None,
                "interview_questions": len(final_state.get("interview_session", {}).get("questions", [])) if final_state.get("interview_session") else None,
            },
            "final_state": {
                "extracted_profile": final_state.get("extracted_profile"),
                "ats_report": final_state.get("ats_report"),
                "discovered_jobs": final_state.get("discovered_jobs"),
                "job_matches": final_state.get("job_matches"),
                "career_roadmap": final_state.get("career_roadmap"),
                "discovered_events": final_state.get("discovered_events"),
                "interview_session": final_state.get("interview_session"),
            }
        }
        WORKFLOW_RUNS[workflow_id] = run_record
        return run_record

    except Exception as e:
        logger.error("Workflow invocation failed: %s", str(e), exc_info=True)
        failed_record = {
            "run_id": workflow_id,
            "status": "failed",
            "error": str(e),
            "elapsed_seconds": 0,
            "agent_executions": [],
            "messages": [{"role": "system", "content": f"Workflow failed with error: {str(e)}"}],
        }
        WORKFLOW_RUNS[workflow_id] = failed_record
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")


@router.get("/runs")
async def list_workflow_runs():
    """List historical agent execution runs."""
    return {
        "runs": list(WORKFLOW_RUNS.values()),
        "total_runs": len(WORKFLOW_RUNS),
    }


@router.get("/runs/{run_id}")
async def get_workflow_run(run_id: str):
    """Retrieve detailed execution trace for an agent workflow run."""
    if run_id not in WORKFLOW_RUNS:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return WORKFLOW_RUNS[run_id]

