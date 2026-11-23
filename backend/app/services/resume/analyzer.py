"""
Resume LLM Review & Content Refinement Analyzer.
Uses LLMManager to generate evidence-backed bullet point improvements and audit claims.
Falls back seamlessly to deterministic rules if no LLM is configured.
"""

import json
import logging
from typing import Any, Dict, Optional
from app.llm.base import LLMMessage
from app.llm.manager import llm_manager

logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    """LLM-assisted resume reviewer."""

    async def _run_llm_review(
        self,
        resume_text: str,
        profile: Optional[Dict[str, Any]] = None,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        prompt = (
            "You are CareerPilot AI's Senior Resume Critic and ATS Optimization specialist.\n"
            "Review the candidate's resume text and provide actionable, honest feedback.\n"
            "Rules:\n"
            "1. NEVER invent metrics or fabricate projects.\n"
            "2. Suggest Google X-Y-Z formula placeholders for unquantified bullets: Accomplished [X], measured by [Y], by doing [Z].\n"
            "3. Identify vague verbs or keyword stuffing.\n"
            "4. Return valid JSON only.\n\n"
            f"RESUME TEXT:\n{resume_text[:2000]}\n\n"
        )
        if job_description:
            prompt += f"TARGET JOB DESCRIPTION:\n{job_description[:1000]}\n\n"

        prompt += (
            "Output JSON with keys:\n"
            "- vague_descriptions (list of strings)\n"
            "- bullet_suggestions (list of {original, improved, rationale})\n"
            "- missing_evidence_skills (list of strings)\n"
            "- summary_feedback (string)\n"
        )

        messages = [
            LLMMessage(role="system", content="You are a strict, truthful career intelligence resume analyzer. Return JSON."),
            LLMMessage(role="user", content=prompt),
        ]

        response = await llm_manager.generate(
            messages=messages,
            temperature=0.2,
            max_tokens=1200,
            response_format="json",
        )

        try:
            parsed_json = json.loads(response.content)
        except Exception:
            parsed_json = {
                "summary_feedback": response.content,
                "bullet_suggestions": [],
                "vague_descriptions": [],
                "missing_evidence_skills": [],
            }

        parsed_json["provider_used"] = response.provider_name
        parsed_json["model_name"] = response.model_name
        parsed_json["is_proprietary"] = response.is_proprietary
        parsed_json["is_fallback"] = response.is_fallback
        parsed_json["latency_ms"] = response.latency_ms

        return parsed_json

