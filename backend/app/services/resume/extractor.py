"""
Resume Extractor Bridge Service.
Extracts candidate information into dictionary format for AgentState.
"""

from typing import Any, Dict
from app.services.resume.ats import ats_validator


class ResumeExtractor:
    """Extracts structured resume data."""

    def extract(self, resume_text: str) -> Dict[str, Any]:
        profile = ats_validator.extract_structure(resume_text)
        return {
            "name": profile.name,
            "email": profile.email,
            "phone": profile.phone,
            "linkedin_url": profile.linkedin_url,
            "github_url": profile.github_url,
            "portfolio_url": profile.portfolio_url,
            "summary": profile.summary,
            "skills": {
                "technical": profile.skills,
                "soft": profile.soft_skills,
            },
            "education": profile.education,
            "experience": profile.experience,
            "projects": profile.projects,
            "certifications": profile.certifications,
            "raw_sections": profile.raw_sections,
        }

