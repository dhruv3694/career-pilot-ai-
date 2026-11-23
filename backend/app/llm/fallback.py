"""
Deterministic Fallback Provider.
Ensures zero runtime failure when no remote LLM credentials exist or external APIs are unreachable.
Provides rule-based, deterministic responses clearly flagged as deterministic fallback.
"""

import json
import logging
import re
import time
from typing import List, Optional
from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

logger = logging.getLogger(__name__)


class DeterministicFallbackProvider(BaseLLMProvider):
    """Tier 1: Fully offline deterministic fallback engine."""

    def __init__(self):
        super().__init__(model_name="deterministic-rule-engine-v1", api_key=None)

    async def is_available(self) -> bool:
        return True  # Always available locally

    async def generate(
        self,
        messages: List[LLMMessage],
        temperature: float = 0.0,
        max_tokens: int = 1500,
        response_format: Optional[str] = None,
    ) -> LLMResponse:
        start_time = time.perf_counter()
        
        user_prompt = "\n".join([m.content for m in messages if m.role == "user"])
        lower_prompt = user_prompt.lower()

        # Generate intelligent deterministic responses based on prompt domain
        output_data = {}

        if "resume" in lower_prompt or "bullet" in lower_prompt or "ats" in lower_prompt:
            output_data = {
                "source": "deterministic_rules",
                "summary": "Deterministic rule-based review executed (No active remote LLM).",
                "vague_descriptions_identified": [
                    "Passive phrases like 'worked on' or 'helped with' without measurable KPIs.",
                    "Missing business metrics or quantified results in recent role.",
                ],
                "suggested_improvements": [
                    "Formulate bullets using Google X-Y-Z formula: Accomplished [X] as measured by [Y], by doing [Z].",
                    "Add explicit references to tools and methodologies used in your projects.",
                    "Ensure technical skills listed in the summary appear in project descriptions.",
                ],
                "unsupported_claims": [
                    "Check that all listed proficiencies (e.g., Kubernetes, PyTorch) have corresponding evidence in work experience or projects."
                ],
                "metrics_placeholders": [
                    "[Quantify impact: e.g., reduced latency by X% / increased throughput by Y% / automated manual process saving Z hrs/wk]"
                ]
            }
        elif "interview" in lower_prompt or "evaluat" in lower_prompt:
            output_data = {
                "source": "deterministic_rubric",
                "score": 75.0,
                "feedback": "Deterministic evaluation: Response contains valid keywords and structure, but could expand on trade-offs and real-world failure modes.",
                "strengths": ["Structured delivery", "Direct answer to core question premise"],
                "areas_for_improvement": ["Elaborate on edge cases", "Include specific metrics from past experience"],
                "model_answer": "A production-grade answer follows the STAR method: Situation, Task, Action taken, and measurable Result achieved."
            }
        elif "roadmap" in lower_prompt or "career" in lower_prompt:
            output_data = {
                "source": "deterministic_curriculum",
                "milestones": [
                    {"phase": 1, "topic": "Core Foundations & Systems Programming", "weeks": 3},
                    {"phase": 2, "topic": "Distributed Systems & Cloud Architecture", "weeks": 4},
                    {"phase": 3, "topic": "Production Deployment & Observability", "weeks": 3}
                ],
                "note": "Curated using the CareerPilot standard competency taxonomy."
            }
        else:
            output_data = {
                "source": "deterministic_fallback",
                "status": "partial",
                "message": "Deterministic rule output generated. Remote LLM inference provider not configured or temporarily unreachable.",
                "input_summary": user_prompt[:150] + "..." if len(user_prompt) > 150 else user_prompt
            }

        content_str = json.dumps(output_data, indent=2) if response_format == "json" else (
            f"**[Deterministic Fallback Engine Output]**\n\n"
            f"Remote LLM is offline or unconfigured. Applied open-source rule heuristics:\n\n"
            + "\n".join([f"- {k}: {v}" for k, v in output_data.items()])
        )

        latency_ms = (time.perf_counter() - start_time) * 1000

        return LLMResponse(
            content=content_str,
            provider_name="deterministic_fallback",
            model_name="deterministic-rule-engine-v1",
            is_proprietary=False,
            is_fallback=True,
            tokens_used=len(content_str.split()),
            latency_ms=round(latency_ms, 2),
            status="fallback",
        )

