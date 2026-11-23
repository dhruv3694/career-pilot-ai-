"""
Interview Preparation Lab API Router.
Supports question generation from extensive question bank, candidate answer submission,
and transparent rubric-based response evaluation.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.interview.engine import InterviewEngine, QUESTION_BANK
from app.llm.manager import llm_manager
from app.llm.base import LLMMessage

router = APIRouter(prefix="/interview", tags=["Interview Lab"])
logger = logging.getLogger(__name__)

engine = InterviewEngine()


class StartSessionRequest(BaseModel):
    role: str = "software_engineer"
    session_type: str = "technical"  # technical, behavioral, system_design, coding, mixed
    count: int = 5
    skills: List[str] = Field(default_factory=list)


class SubmitAnswerRequest(BaseModel):
    question_id: str
    question: str
    sample_answer: Optional[str] = ""
    candidate_answer: str
    category: Optional[str] = "technical"
    role: Optional[str] = "software_engineer"


@router.get("/roles")
async def list_available_roles():
    """List roles supported in the built-in interview question bank."""
    roles = [
        {"key": "software_engineer", "title": "Software Engineer"},
        {"key": "data_scientist", "title": "Data Scientist"},
        {"key": "ml_engineer", "title": "Machine Learning Engineer"},
        {"key": "frontend_developer", "title": "Frontend Developer"},
        {"key": "backend_developer", "title": "Backend Developer"},
        {"key": "devops_engineer", "title": "DevOps / Cloud Engineer"},
    ]
    return {"roles": roles}


@router.post("/session/start")
async def start_interview_session(payload: StartSessionRequest):
    """Start an interactive interview practice session."""
    session = engine.generate_session(
        role=payload.role,
        skills=payload.skills,
        session_type=payload.session_type,
        count=payload.count,
    )
    return {
        "status": "success",
        "session": session,
    }


@router.post("/evaluate")
async def evaluate_candidate_answer(payload: SubmitAnswerRequest):
    """Evaluate candidate response using deterministic rubrics and LLM feedback."""
    clean_answer = payload.candidate_answer.strip()
    if not clean_answer:
        raise HTTPException(status_code=400, detail="Please enter an answer before requesting an evaluation.")
    
    # If the answer is extremely short (e.g. fewer than 10 characters like 'hello'), evaluate and give constructive feedback instead of crashing with HTTP 400!
    if len(clean_answer) < 10:
        return {
            "status": "success",
            "evaluation": {
                "question_id": payload.question_id,
                "score": 5.0,
                "overall_score": 5.0,
                "rating": "Needs Practice",
                "feedback": "Your answer is too brief to demonstrate technical competence. Aim to provide a comprehensive response explaining key concepts, architecture, and practical examples.",
                "strengths": ["Submitted response for evaluation"],
                "improvements": [
                    "Elaborate on the core concepts with specific definitions",
                    "Structure your answer using the STAR method or clear bullet points",
                    "Provide concrete code or architectural examples"
                ],
                "model_answer": payload.sample_answer or "A strong answer thoroughly covers technical trade-offs, internal mechanisms, and real-world performance impacts.",
                "llm_feedback": "Answer provided is under 10 characters. A thorough answer should explain the 'why' and 'how' behind the concept rather than a greeting or short phrase.",
                "provider_used": "deterministic_fallback",
                "is_proprietary": False,
                "is_fallback": True,
            }
        }

    # 1. Deterministic Rubric Evaluation
    question_payload = {
        "id": payload.question_id,
        "question": payload.question,
        "category": payload.category or "technical",
        "sample_answer": payload.sample_answer or "",
    }
    eval_result = await engine.evaluate_response(
        question=question_payload,
        response=payload.candidate_answer,
    )
    eval_dict = eval_result.model_dump()
    eval_dict["overall_score"] = round(eval_result.score, 1)
    eval_dict["improvements"] = eval_result.areas_for_improvement
    eval_dict["rating"] = "Strong" if eval_result.score >= 75 else "Proficient" if eval_result.score >= 55 else "Needs Practice"

    # 2. Try LLM enrichment if available
    try:
        prompt = (
            f"Interview Question: {payload.question}\n"
            f"Candidate Answer: {payload.candidate_answer}\n"
            f"Target Sample Answer: {payload.sample_answer}\n"
            "Evaluate this candidate answer strictly and constructively.\n"
            "Provide:\n"
            "1. Specific Strengths\n"
            "2. Areas for improvement (edge cases, depth, STAR structure)\n"
            "3. Revised model answer snippet"
        )
        llm_resp = await llm_manager.generate(
            messages=[
                LLMMessage(role="system", content="You are a principal technical interviewer evaluating candidates with high standards."),
                LLMMessage(role="user", content=prompt),
            ],
            max_tokens=400,
        )
        eval_dict["llm_feedback"] = llm_resp.content
        eval_dict["provider_used"] = llm_resp.provider_name
        eval_dict["is_proprietary"] = llm_resp.is_proprietary
        eval_dict["is_fallback"] = llm_resp.is_fallback
    except Exception as exc:
        eval_dict["llm_feedback"] = "Deterministic rubric evaluation completed. No remote LLM used."
        eval_dict["provider_used"] = "deterministic_rubric"
        eval_dict["is_proprietary"] = False
        eval_dict["is_fallback"] = True

    return {
        "status": "success",
        "evaluation": eval_dict,
    }

