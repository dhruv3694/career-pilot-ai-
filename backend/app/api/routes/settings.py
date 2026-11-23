"""
Settings, Health, and Human Approval API Router.
Reports LLM provider health status, open-source compliance inventory,
and human-in-the-loop approval requests for consequential actions.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.manager import llm_manager
from app.core.config import settings

router = APIRouter(prefix="/settings", tags=["Settings & Approvals"])

# In-memory approval requests store
APPROVAL_REQUESTS: List[Dict[str, Any]] = [
    {
        "id": "appr_001",
        "action_type": "submit_application",
        "title": "Submit Job Application to Canonical",
        "description": "Draft prepared for 'Junior Python / Backend Engineer'. Requires your review and confirmation before directing to the official portal.",
        "payload": {
            "employer": "Canonical",
            "role": "Junior Python / Backend Engineer",
            "application_url": "https://boards.greenhouse.io/canonical/jobs/junior-backend",
        },
        "status": "pending",
        "created_at": "2026-10-22T23:59:00Z",
    },
    {
        "id": "appr_002",
        "action_type": "send_recruiter_email",
        "title": "Send Introduction Email to University Placement Coordinator",
        "description": "Draft email to placement@unipune.ac.in regarding IT campus drive registration.",
        "payload": {
            "recipient": "placement@unipune.ac.in",
            "subject": "Inquiry regarding Campus Recruitment Drive Dec 2026",
        },
        "status": "pending",
        "created_at": "2026-10-22T23:59:30Z",
    }
]


class ApprovalDecisionRequest(BaseModel):
    decision: str = Field(..., pattern=r"^(approve|reject)$")
    comments: Optional[str] = ""


@router.get("/providers")
async def get_providers_status():
    """Retrieve availability and health status of all LLM providers and open-weight models."""
    status = await llm_manager.get_provider_status()
    return {
        "providers": status,
        "active_priority": settings.llm_provider_priority_list,
        "total_requests": llm_manager.total_requests,
        "successful_requests": llm_manager.successful_requests,
        "fallback_requests": llm_manager.fallback_requests,
        "total_tokens_consumed": llm_manager.total_tokens_consumed,
        "recent_history": llm_manager.provider_history[-10:],
    }


@router.get("/compliance-inventory")
async def get_compliance_inventory():
    """Detailed open-source architecture tier breakdown."""
    return {
        "tier_1_open_source": [
            {"component": "Agent Orchestration", "package": "LangGraph (StateGraph)", "license": "MIT"},
            {"component": "Backend API", "package": "FastAPI", "license": "MIT"},
            {"component": "Database & ORM", "package": "SQLite / SQLAlchemy 2.0", "license": "MIT"},
            {"component": "Document Ingestion", "package": "PyMuPDF (fitz) & python-docx", "license": "AGPL-3.0 / MIT"},
            {"component": "Vector Store & Retrieval", "package": "Local Vector Store / TF-IDF Cosine", "license": "Apache-2.0"},
            {"component": "MCP Server", "package": "Official Python MCP SDK (FastMCP)", "license": "MIT"},
            {"component": "Frontend UI", "package": "React 18 / Tailwind CSS / Lucide", "license": "MIT"},
        ],
        "tier_2_open_weight_models": [
            {"model": "Llama 3.1 70B Versatile", "provider": "Groq API (Hosted Inference)", "license": "Meta Llama 3.1 Community License"},
            {"model": "Llama 3.1 8B Instant", "provider": "Groq API (Hosted Inference)", "license": "Meta Llama 3.1 Community License"},
            {"model": "Mixtral 8x7B Instruct", "provider": "Groq API (Hosted Inference)", "license": "Apache-2.0"},
        ],
        "tier_3_proprietary_adapters": [
            {"model": "Google Gemini 1.5 Flash", "provider": "Google Generative AI", "license": "Proprietary Commercial Service"},
        ],
        "tier_1_offline_fallback": [
            {"name": "CareerPilot Deterministic Rule Engine", "provider": "Local Python heuristics", "license": "MIT"},
        ]
    }


@router.get("/approvals")
async def list_approval_requests():
    """List pending consequential action approval requests."""
    return {
        "approvals": APPROVAL_REQUESTS,
        "pending_count": sum(1 for a in APPROVAL_REQUESTS if a["status"] == "pending"),
    }


@router.post("/approvals/{request_id}/decision")
async def decide_approval_request(request_id: str, payload: ApprovalDecisionRequest):
    """Approve or reject a consequential action request."""
    req = next((a for a in APPROVAL_REQUESTS if a["id"] == request_id), None)
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")

    req["status"] = "approved" if payload.decision == "approve" else "rejected"
    req["decision_comments"] = payload.comments
    req["resolved_at"] = "2026-10-23T00:00:00Z"

    return {
        "status": "success",
        "message": f"Action {payload.decision}d successfully.",
        "request": req,
    }

