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

    async def generate_tailored_application(
        self,
        profile: Dict[str, Any],
        job_title: str,
        employer: Optional[str] = None,
        job_description: Optional[str] = None,
        required_skills: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        """Generate a tailored resume and customized cover letter without requiring local heavy models."""
        candidate_name = profile.get("name", "Candidate")
        skills = profile.get("skills", [])
        experience = profile.get("experience", [])
        company_str = f" at {employer}" if employer else ""
        skills_str = ", ".join(skills[:15]) if skills else "general software development"
        req_str = ", ".join(required_skills[:10]) if required_skills else "the required core qualifications"

        prompt = (
            f"You are an expert career strategist. Create a tailored resume profile and professional cover letter "
            f"for candidate '{candidate_name}' applying for '{job_title}'{company_str}.\n"
            f"Candidate verified skills: {skills_str}\n"
            f"Job requirements: {req_str}\n"
            f"Job details: {job_description[:800] if job_description else 'Focus on high impact, clean communication.'}\n\n"
            "Return valid JSON with the following exact keys:\n"
            "- tailored_summary: A punchy 2-3 sentence executive summary tailored for this specific role.\n"
            "- prioritized_skills: list of the top 8-12 skills most relevant to this job description.\n"
            "- tailored_bullet_points: list of 4-6 achievement-oriented bullet points highlighting relevant experience.\n"
            "- cover_letter: A 3-4 paragraph persuasive, tailored cover letter addressed to the hiring manager.\n"
        )

        messages = [
            LLMMessage(role="system", content="You are a professional career coach and executive resume writer. Output JSON only."),
            LLMMessage(role="user", content=prompt),
        ]

        try:
            response = await llm_manager.generate(
                messages=messages,
                temperature=0.3,
                max_tokens=1500,
                response_format="json",
            )
            data = json.loads(response.content)
        except Exception:
            # Deterministic, high-quality rule-based fallback without any cloud or local LLM requirement
            data = {
                "tailored_summary": (
                    f"Results-oriented professional offering proven expertise in {skills_str}. "
                    f"Excited to contribute to {employer or 'your team'} as a {job_title}, leveraging strong problem-solving "
                    f"and engineering best practices to meet key organizational objectives."
                ),
                "prioritized_skills": [s for s in skills if required_skills and any(req.lower() in s.lower() for req in required_skills)] or skills[:8],
                "tailored_bullet_points": [
                    f"Architected and deployed scalable solutions utilizing {skills[0] if skills else 'modern tools'}, driving efficiency and reliable performance.",
                    f"Collaborated cross-functionally to deliver feature specifications aligning with {job_title} requirements and rigorous quality standards.",
                    f"Streamlined workflows and code reviews, improving maintainability and reducing delivery lead times."
                ],
                "cover_letter": (
                    f"Dear Hiring Team at {employer or 'the company'},\n\n"
                    f"I am writing to express my strong enthusiasm for the {job_title} position. With my background in {skills_str}, "
                    f"I have developed a disciplined approach to software craftsmanship and team collaboration.\n\n"
                    f"Throughout my work, I have focused on building resilient systems and translating technical specifications into measurable results. "
                    f"The opportunity to bring my experience with {req_str} to your team is particularly compelling.\n\n"
                    f"Thank you for your time and consideration. I look forward to discussing how my skills and background can contribute to your goals.\n\n"
                    f"Sincerely,\n{candidate_name}"
                )
            }
        return data

