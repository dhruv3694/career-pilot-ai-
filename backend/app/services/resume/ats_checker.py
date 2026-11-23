"""
ATS Checker Bridge Service.
Runs deterministic ATS validation and returns dictionary output for AgentState.
"""

from typing import Any, Dict, Optional
from app.services.resume.ats import ats_validator


class ATSChecker:
    """Executes deterministic ATS compatibility assessment."""

    def check(
        self,
        resume_text: str,
        profile: Optional[Dict[str, Any]] = None,
        job_description: Optional[str] = None,
    ) -> Dict[str, Any]:
        report = ats_validator.evaluate(
            raw_text=resume_text,
            job_description=job_description,
        )
        return report.model_dump()

