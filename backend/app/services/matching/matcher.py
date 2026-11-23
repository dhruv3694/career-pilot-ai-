"""
Job-candidate matching service.

Provides deterministic, transparent scoring of candidate-job fit across
multiple dimensions: skill coverage, preferred skills, experience,
role alignment, and location compatibility.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable weights – must sum to 1.0
# ---------------------------------------------------------------------------
SKILL_WEIGHT: float = 0.35
PREFERRED_WEIGHT: float = 0.10
EXPERIENCE_WEIGHT: float = 0.25
ROLE_WEIGHT: float = 0.20
LOCATION_WEIGHT: float = 0.10

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class SkillGap(BaseModel):
    """A single skill gap between candidate and job requirements."""

    skill: str
    importance: str = Field(
        ..., description="required or preferred", pattern=r"^(required|preferred)$"
    )
    suggestion: str


class MatchResult(BaseModel):
    """Full match result with transparent scoring breakdown."""

    overall_score: float = Field(..., ge=0, le=100)
    skill_coverage_score: float = Field(..., ge=0, le=100)
    preferred_coverage_score: float = Field(..., ge=0, le=100)
    experience_score: float = Field(..., ge=0, le=100)
    role_alignment_score: float = Field(..., ge=0, le=100)
    location_score: float = Field(..., ge=0, le=100)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    matched_skills: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TOKENIZE_RE = re.compile(r"[^a-z0-9#+.]+")


def _normalise(text: str) -> str:
    """Lower-case, strip, collapse whitespace."""
    return text.strip().lower()


def _tokenize(text: str) -> set[str]:
    """Split text into a bag-of-words (lowercase)."""
    return {w for w in _TOKENIZE_RE.split(text.lower()) if w}


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two sets."""
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _overlap(a: set[str], b: set[str]) -> float:
    """Overlap coefficient – proportion of *smaller* set present in both."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _skill_set(skills: list[str] | None) -> set[str]:
    """Normalise a list of skill strings into a comparable set."""
    if not skills:
        return set()
    return {_normalise(s) for s in skills if s}


# ---------------------------------------------------------------------------
# Main service
# ---------------------------------------------------------------------------


class JobMatcher:
    """Deterministic job-candidate matcher with configurable weights."""

    def __init__(
        self,
        skill_weight: float = SKILL_WEIGHT,
        preferred_weight: float = PREFERRED_WEIGHT,
        experience_weight: float = EXPERIENCE_WEIGHT,
        role_weight: float = ROLE_WEIGHT,
        location_weight: float = LOCATION_WEIGHT,
    ) -> None:
        self.skill_weight = skill_weight
        self.preferred_weight = preferred_weight
        self.experience_weight = experience_weight
        self.role_weight = role_weight
        self.location_weight = location_weight

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(self, candidate_profile: dict[str, Any], job: dict[str, Any]) -> MatchResult:
        """Score a candidate against a single job posting.

        Parameters
        ----------
        candidate_profile:
            Expected keys: ``skills`` (list[str]), ``experience`` (list[dict]),
            ``summary`` (str), ``location_preferences`` (dict with keys like
            ``preferred_locations``, ``open_to_remote``).
        job:
            Expected keys: ``title`` (str), ``description`` (str),
            ``required_skills`` (list[str]), ``preferred_skills`` (list[str]),
            ``requirements`` (dict with keys like ``min_years``, ``education``),
            ``location`` (str), ``work_mode`` (str – remote/hybrid/onsite).
        """
        candidate_skills_raw = candidate_profile.get("skills") or []
        if isinstance(candidate_skills_raw, dict):
            candidate_skills = candidate_skills_raw.get("technical", []) + candidate_skills_raw.get("soft", [])
        else:
            candidate_skills = candidate_skills_raw
        required_skills = job.get("required_skills") or []
        preferred_skills = job.get("preferred_skills") or []
        candidate_experience = candidate_profile.get("experience") or []
        candidate_summary = candidate_profile.get("summary", "")
        candidate_prefs = candidate_profile.get("location_preferences") or {}
        job_title = job.get("title", "")
        job_desc = job.get("description", "")
        job_requirements = job.get("requirements") or {}
        job_location = job.get("location", "")
        job_work_mode = job.get("work_mode", "")

        # Compute individual scores (0-100)
        skill_score = self._compute_skill_coverage(candidate_skills, required_skills)
        preferred_score = self._compute_preferred_coverage(candidate_skills, preferred_skills)
        experience_score = self._compute_experience_match(candidate_experience, job_requirements)
        role_score = self._compute_role_alignment(candidate_summary, job_title, job_desc)
        location_score = self._compute_location_match(candidate_prefs, job_location, job_work_mode)

        # Weighted overall score
        overall = (
            skill_score * self.skill_weight
            + preferred_score * self.preferred_weight
            + experience_score * self.experience_weight
            + role_score * self.role_weight
            + location_score * self.location_weight
        )

        # Skill analysis
        cand_set = _skill_set(candidate_skills)
        req_set = _skill_set(required_skills)
        pref_set = _skill_set(preferred_skills)
        matched = sorted(cand_set & (req_set | pref_set))

        gaps = self._identify_skill_gaps(candidate_skills, required_skills, preferred_skills)
        recommendations = self._build_recommendations(
            overall, skill_score, experience_score, role_score, location_score, gaps
        )

        return MatchResult(
            overall_score=round(overall, 2),
            skill_coverage_score=round(skill_score, 2),
            preferred_coverage_score=round(preferred_score, 2),
            experience_score=round(experience_score, 2),
            role_alignment_score=round(role_score, 2),
            location_score=round(location_score, 2),
            skill_gaps=gaps,
            matched_skills=matched,
            recommendations=recommendations,
            score_breakdown={
                "skill_coverage": round(skill_score * self.skill_weight, 2),
                "preferred_coverage": round(preferred_score * self.preferred_weight, 2),
                "experience": round(experience_score * self.experience_weight, 2),
                "role_alignment": round(role_score * self.role_weight, 2),
                "location": round(location_score * self.location_weight, 2),
            },
        )

    # ------------------------------------------------------------------
    # Scoring components
    # ------------------------------------------------------------------

    def _compute_skill_coverage(
        self, candidate_skills: list[str], required_skills: list[str]
    ) -> float:
        """Percentage of required skills the candidate possesses (0-100)."""
        if not required_skills:
            return 100.0
        cand = _skill_set(candidate_skills)
        req = _skill_set(required_skills)
        if not req:
            return 100.0
        covered = len(cand & req)
        return (covered / len(req)) * 100.0

    def _compute_preferred_coverage(
        self, candidate_skills: list[str], preferred_skills: list[str]
    ) -> float:
        """Percentage of preferred (nice-to-have) skills the candidate has (0-100)."""
        if not preferred_skills:
            return 100.0
        cand = _skill_set(candidate_skills)
        pref = _skill_set(preferred_skills)
        if not pref:
            return 100.0
        covered = len(cand & pref)
        return (covered / len(pref)) * 100.0

    def _compute_experience_match(
        self, candidate_exp: list[dict[str, Any]], job_requirements: dict[str, Any]
    ) -> float:
        """Score experience fit (0-100).

        Considers total years of experience versus job minimum and
        education level alignment.
        """
        min_years: float = float(job_requirements.get("min_years", 0))
        required_education: str = _normalise(job_requirements.get("education", ""))

        # Total candidate years
        total_years: float = 0.0
        has_education_match: bool = False
        candidate_education: str = ""

        for exp in candidate_exp:
            years = exp.get("years", 0)
            if isinstance(years, (int, float)):
                total_years += years
            # Check education from experience entries (if embedded)
            edu = _normalise(exp.get("education", ""))
            if edu:
                candidate_education = edu

        # Years score – linearly ramp up to min_years, slight bonus above
        if min_years <= 0:
            years_score = 100.0
        elif total_years >= min_years:
            # Bonus capped at 10 points for exceeding by up to 5 years
            bonus = min((total_years - min_years) / 5.0 * 10.0, 10.0)
            years_score = min(100.0, 90.0 + bonus)
        else:
            years_score = max(0.0, (total_years / min_years) * 90.0)

        # Education match – add up to 10 points or subtract up to 10
        education_adjustment: float = 0.0
        if required_education:
            edu_levels = {
                "high school": 1,
                "associate": 2,
                "bachelor": 3,
                "bachelors": 3,
                "master": 4,
                "masters": 4,
                "phd": 5,
                "doctorate": 5,
            }
            req_level = 0
            cand_level = 0
            for key, level in edu_levels.items():
                if key in required_education:
                    req_level = max(req_level, level)
                if key in candidate_education:
                    cand_level = max(cand_level, level)

            if cand_level >= req_level and req_level > 0:
                education_adjustment = 5.0
            elif req_level > 0 and cand_level > 0 and cand_level < req_level:
                education_adjustment = -5.0

        return max(0.0, min(100.0, years_score + education_adjustment))

    def _compute_role_alignment(
        self, candidate_summary: str, job_title: str, job_desc: str
    ) -> float:
        """Score how well the candidate's background aligns with the role (0-100).

        Uses a combination of Jaccard and overlap coefficient on tokenised text.
        """
        if not candidate_summary:
            return 50.0  # neutral when no summary provided

        cand_tokens = _tokenize(candidate_summary)
        job_tokens = _tokenize(f"{job_title} {job_desc}")

        if not cand_tokens or not job_tokens:
            return 50.0

        jaccard = _jaccard(cand_tokens, job_tokens)
        overlap = _overlap(cand_tokens, job_tokens)

        # Blend: favour overlap (more forgiving for length difference)
        blended = jaccard * 0.3 + overlap * 0.7
        return min(100.0, blended * 100.0)

    def _compute_location_match(
        self, candidate_prefs: dict[str, Any], job_location: str, job_work_mode: str
    ) -> float:
        """Score location compatibility (0-100).

        Remote jobs always score high. Otherwise compare preferred
        locations with the job's location.
        """
        mode = _normalise(job_work_mode)
        open_to_remote = candidate_prefs.get("open_to_remote", False)

        # Remote job → instant compatibility if candidate is open
        if mode == "remote":
            return 100.0 if open_to_remote else 80.0

        # No preferences specified – assume flexible
        preferred_locations: list[str] = candidate_prefs.get("preferred_locations") or []
        if not preferred_locations:
            return 70.0  # neutral-ish

        job_loc = _normalise(job_location)
        if not job_loc:
            return 70.0

        # Check for direct or substring matches
        for pref in preferred_locations:
            pref_n = _normalise(pref)
            if pref_n in job_loc or job_loc in pref_n:
                return 100.0

        # Hybrid mode is more flexible
        if mode == "hybrid":
            return 50.0

        return 30.0  # onsite with no location match

    # ------------------------------------------------------------------
    # Skill gap analysis
    # ------------------------------------------------------------------

    def _identify_skill_gaps(
        self,
        candidate_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str],
    ) -> list[SkillGap]:
        """Identify missing skills with actionable suggestions."""
        cand = _skill_set(candidate_skills)
        gaps: list[SkillGap] = []

        req = _skill_set(required_skills)
        for skill_raw, skill_norm in zip(required_skills, [_normalise(s) for s in required_skills]):
            if skill_norm and skill_norm not in cand:
                gaps.append(
                    SkillGap(
                        skill=skill_raw,
                        importance="required",
                        suggestion=f"Consider taking a course or building a project with {skill_raw} "
                        f"to strengthen your application.",
                    )
                )

        pref = _skill_set(preferred_skills)
        for skill_raw, skill_norm in zip(
            preferred_skills, [_normalise(s) for s in preferred_skills]
        ):
            if skill_norm and skill_norm not in cand and skill_norm not in req:
                gaps.append(
                    SkillGap(
                        skill=skill_raw,
                        importance="preferred",
                        suggestion=f"Learning {skill_raw} could give you a competitive edge for this role.",
                    )
                )

        return gaps

    # ------------------------------------------------------------------
    # Recommendations
    # ------------------------------------------------------------------

    @staticmethod
    def _build_recommendations(
        overall: float,
        skill_score: float,
        experience_score: float,
        role_score: float,
        location_score: float,
        gaps: list[SkillGap],
    ) -> list[str]:
        """Generate human-readable recommendations based on scores."""
        recs: list[str] = []

        if overall >= 80:
            recs.append("Strong match! You meet most of the job requirements.")
        elif overall >= 60:
            recs.append("Good potential match. Address the gaps below to strengthen your application.")
        elif overall >= 40:
            recs.append("Moderate match. Consider upskilling in the identified areas before applying.")
        else:
            recs.append(
                "This role may require significant preparation. Focus on building the required skills first."
            )

        if skill_score < 50:
            required_gaps = [g.skill for g in gaps if g.importance == "required"]
            if required_gaps:
                recs.append(
                    f"Priority skill gaps: {', '.join(required_gaps[:5])}. "
                    f"Focus on these required skills first."
                )

        if experience_score < 50:
            recs.append(
                "Your experience level may be below the job requirements. "
                "Highlight transferable skills and relevant projects."
            )

        if role_score < 40:
            recs.append(
                "Your profile summary doesn't closely align with this role. "
                "Tailor your resume summary to highlight relevant experience."
            )

        if location_score < 50:
            recs.append(
                "Location may be a concern. Check if the employer offers relocation assistance "
                "or remote options."
            )

        return recs
