"""
Deterministic ATS-Style Resume Validation Engine and Structured Extractor.
Implements rule-based ATS evaluation, structured section parsing, evidence extraction,
job-specific keyword matching, and document revision/export.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Standard resume sections recognized by modern ATS parsers
STANDARD_SECTIONS = [
    "summary",
    "experience",
    "education",
    "skills",
    "projects",
    "certifications",
]

SECTION_KEYWORDS = {
    "summary": ["summary", "profile", "professional summary", "about me", "objective", "executive summary"],
    "experience": ["experience", "employment", "work history", "work experience", "professional experience", "internships"],
    "education": ["education", "academic background", "qualifications", "academics", "degrees"],
    "skills": ["skills", "technical skills", "competencies", "technologies", "core competencies", "tools"],
    "projects": ["projects", "personal projects", "academic projects", "key projects"],
    "certifications": ["certifications", "licenses", "certificates", "credentials", "courses"],
}

COMMON_TECH_SKILLS = [
    "python", "javascript", "typescript", "react", "node.js", "nodejs", "fastapi", "django",
    "flask", "sql", "postgresql", "mysql", "sqlite", "mongodb", "redis", "docker", "kubernetes",
    "aws", "azure", "gcp", "git", "ci/cd", "linux", "html", "css", "tailwind", "c++", "c#",
    "java", "spring boot", "pandas", "numpy", "pytorch", "tensorflow", "scikit-learn",
    "rest api", "graphql", "microservices", "langchain", "langgraph", "llm", "nlp"
]

COMMON_SOFT_SKILLS = [
    "communication", "teamwork", "leadership", "problem solving", "critical thinking",
    "adaptability", "time management", "collaboration", "analytical", "agile", "scrum"
]

ACTION_VERBS = [
    "achieved", "architected", "built", "created", "designed", "developed", "deployed",
    "engineered", "established", "implemented", "improved", "increased", "initiated",
    "launched", "led", "managed", "optimized", "orchestrated", "reduced", "spearheaded",
    "streamlined", "transformed"
]


class ExtractedProfile(BaseModel):
    """Normalized structured profile extracted from resume text."""
    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    education: List[Dict[str, Any]] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    raw_sections: Dict[str, str] = Field(default_factory=dict)


class ATSScoreBreakdown(BaseModel):
    """Detailed category scoring."""
    section_structure_score: float = Field(..., ge=0, le=100)
    contact_completeness_score: float = Field(..., ge=0, le=100)
    content_impact_score: float = Field(..., ge=0, le=100)
    formatting_quality_score: float = Field(..., ge=0, le=100)
    skill_consistency_score: float = Field(..., ge=0, le=100)
    job_alignment_score: Optional[float] = None


class ATSCheckDetail(BaseModel):
    """Result of a single ATS check."""
    name: str
    passed: bool
    score: float
    max_score: float
    details: str
    severity: str = "info"  # info, warning, critical


class ComprehensiveATSReport(BaseModel):
    """Full ATS validation report."""
    overall_score: float = Field(..., ge=0, le=100)
    category_scores: ATSScoreBreakdown
    checks: List[ATSCheckDetail]
    found_sections: List[str]
    missing_sections: List[str]
    formatting_warnings: List[str]
    suggestions: List[str]
    detected_skills: List[str]
    evidence_items: List[Dict[str, Any]] = Field(default_factory=list)
    disclaimer: str = (
        "CareerPilot AI uses transparent heuristic checks and job-description semantic matching. "
        "Real-world employer ATS systems differ by company and vendor configuration. "
        "No score guarantees an interview or job offer."
    )


class ATSValidatorService:
    """Core ATS validation engine."""

    def extract_structure(self, raw_text: str) -> ExtractedProfile:
        """Parse raw resume text into structured candidate profile."""
        lines = [line.strip() for line in raw_text.split("\n") if line.strip()]
        profile = ExtractedProfile()

        if not lines:
            return profile

        # 1. Contact details extraction
        # Candidate name: typically the first prominent non-empty line
        for line in lines[:5]:
            if not re.search(r"@|github|linkedin|http|\+?\d{9,}", line, re.I) and len(line.split()) <= 4:
                profile.name = line.strip()
                break

        # Email
        email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", raw_text)
        if email_match:
            profile.email = email_match.group(0)

        # Phone
        phone_match = re.search(r"(\+?\d{1,3}[-.\s]?)?(\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}", raw_text)
        if phone_match and len(phone_match.group(0)) >= 10:
            profile.phone = phone_match.group(0).strip()

        # URLs
        linkedin_match = re.search(r"(https?://)?(www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+", raw_text, re.I)
        if linkedin_match:
            profile.linkedin_url = linkedin_match.group(0)

        github_match = re.search(r"(https?://)?(www\.)?github\.com/[a-zA-Z0-9_-]+", raw_text, re.I)
        if github_match:
            profile.github_url = github_match.group(0)

        portfolio_match = re.search(r"https?://(?!.*(linkedin|github))[a-zA-Z0-9.-]+\.[a-z]{2,}(/[^\s]*)?", raw_text, re.I)
        if portfolio_match:
            profile.portfolio_url = portfolio_match.group(0)

        # 2. Section Partitioning
        sections: Dict[str, List[str]] = {}
        current_section = "header"
        sections[current_section] = []

        for line in lines:
            normalized_line = line.lower().strip(": ").strip()
            detected_sec = None
            for sec_key, aliases in SECTION_KEYWORDS.items():
                if normalized_line in aliases or any(normalized_line.startswith(a) for a in aliases):
                    detected_sec = sec_key
                    break

            if detected_sec:
                current_section = detected_sec
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections.setdefault(current_section, []).append(line)

        profile.raw_sections = {k: "\n".join(v) for k, v in sections.items()}

        if "summary" in profile.raw_sections:
            profile.summary = profile.raw_sections["summary"].strip()

        # 3. Skills extraction
        raw_skills_text = (profile.raw_sections.get("skills", "") + " " + raw_text).lower()
        extracted_tech = set()
        for skill in COMMON_TECH_SKILLS:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, raw_skills_text):
                extracted_tech.add(skill.title() if len(skill) > 3 else skill.upper())
        profile.skills = sorted(list(extracted_tech))

        extracted_soft = set()
        for s_skill in COMMON_SOFT_SKILLS:
            if re.search(r"\b" + re.escape(s_skill) + r"\b", raw_skills_text):
                extracted_soft.add(s_skill.title())
        profile.soft_skills = sorted(list(extracted_soft))

        # 4. Education Parsing
        if "education" in profile.raw_sections:
            edu_lines = profile.raw_sections["education"].split("\n")
            current_edu = {}
            for el in edu_lines:
                if re.search(r"bachelor|master|b\.s|m\.s|b\.tech|m\.tech|phd|associate|degree|university|college|institute", el, re.I):
                    if current_edu:
                        profile.education.append(current_edu)
                        current_edu = {}
                    current_edu["degree_or_institution"] = el
                year_match = re.search(r"(20\d{2}|19\d{2})", el)
                if year_match and current_edu:
                    current_edu["year"] = year_match.group(0)
            if current_edu:
                profile.education.append(current_edu)

        # 5. Experience Parsing
        if "experience" in profile.raw_sections:
            exp_lines = profile.raw_sections["experience"].split("\n")
            current_role = {}
            bullets = []
            for el in exp_lines:
                # Detect role/company header
                if re.search(r"engineer|developer|intern|manager|lead|analyst|specialist|consultant", el, re.I) and len(el.split()) <= 15:
                    if current_role:
                        current_role["bullets"] = bullets
                        profile.experience.append(current_role)
                        current_role = {}
                        bullets = []
                    current_role["title"] = el
                elif el.startswith(("-", "•", "*")) or (current_role and len(el) > 20):
                    bullets.append(el.lstrip("-•* ").strip())
            if current_role:
                current_role["bullets"] = bullets
                profile.experience.append(current_role)

        # 6. Projects Parsing
        if "projects" in profile.raw_sections:
            proj_lines = profile.raw_sections["projects"].split("\n")
            current_proj = {}
            p_bullets = []
            for pl in proj_lines:
                if len(pl.split()) <= 10 and not pl.startswith(("-", "•", "*")):
                    if current_proj:
                        current_proj["bullets"] = p_bullets
                        profile.projects.append(current_proj)
                        current_proj = {}
                        p_bullets = []
                    current_proj["title"] = pl
                else:
                    p_bullets.append(pl.lstrip("-•* ").strip())
            if current_proj:
                current_proj["bullets"] = p_bullets
                profile.projects.append(current_proj)

        return profile

    def evaluate(
        self,
        raw_text: str,
        profile: Optional[ExtractedProfile] = None,
        job_description: Optional[str] = None,
        required_skills: Optional[List[str]] = None,
        preferred_skills: Optional[List[str]] = None,
    ) -> ComprehensiveATSReport:
        """Run comprehensive deterministic ATS compatibility assessment."""
        if not profile:
            profile = self.extract_structure(raw_text)

        checks: List[ATSCheckDetail] = []
        formatting_warnings: List[str] = []
        suggestions: List[str] = []
        evidence_items: List[Dict[str, Any]] = []

        # Check 1: Standard Section Headings
        found_sections = []
        missing_sections = []
        for sec in STANDARD_SECTIONS:
            if sec in profile.raw_sections and len(profile.raw_sections[sec].strip()) > 10:
                found_sections.append(sec.title())
            else:
                missing_sections.append(sec.title())

        sec_score = (len(found_sections) / len(STANDARD_SECTIONS)) * 100
        sec_passed = len(found_sections) >= 4
        checks.append(ATSCheckDetail(
            name="Standard Section Headings",
            passed=sec_passed,
            score=round(sec_score * 0.20, 1),
            max_score=20.0,
            details=f"Detected {len(found_sections)} of {len(STANDARD_SECTIONS)} standard sections. Found: {', '.join(found_sections)}. Missing: {', '.join(missing_sections) if missing_sections else 'None'}.",
            severity="critical" if "Experience" in missing_sections or "Education" in missing_sections else "warning" if missing_sections else "info"
        ))
        if missing_sections:
            suggestions.append(f"Add explicit '{missing_sections[0]}' section heading to ensure standard ATS parsers index your data accurately.")

        # Check 2: Contact Information Completeness
        contact_points = 0
        max_contact = 5
        contact_details = []
        if profile.email:
            contact_points += 1
            contact_details.append(f"Email: {profile.email}")
        if profile.phone:
            contact_points += 1
            contact_details.append(f"Phone: {profile.phone}")
        if profile.linkedin_url:
            contact_points += 1
            contact_details.append("LinkedIn profile linked")
        if profile.github_url:
            contact_points += 1
            contact_details.append("GitHub profile linked")
        if profile.portfolio_url:
            contact_points += 1
            contact_details.append("Portfolio website linked")

        contact_score = (contact_points / max_contact) * 100
        checks.append(ATSCheckDetail(
            name="Contact Information Completeness",
            passed=contact_points >= 2,
            score=round((contact_points / max_contact) * 15.0, 1),
            max_score=15.0,
            details=f"Found {contact_points}/{max_contact} contact details ({', '.join(contact_details)}).",
            severity="critical" if not profile.email else "info"
        ))
        if not profile.email or not profile.phone:
            suggestions.append("Ensure your email and phone number are clearly visible at the top of the resume.")
        if not profile.linkedin_url and not profile.github_url:
            suggestions.append("Include your LinkedIn or GitHub profile link for technical verification.")

        # Check 3: Content Impact & Action Verbs
        action_verb_count = 0
        raw_lower = raw_text.lower()
        found_verbs = set()
        for verb in ACTION_VERBS:
            if re.search(r"\b" + re.escape(verb) + r"\b", raw_lower):
                action_verb_count += 1
                found_verbs.add(verb)

        # Check quantified metrics (e.g., 20%, $50k, 10x, 5000+ requests, 15+ endpoints)
        metric_matches = re.findall(r"(\b\d+%\b|\$\d+[\d,]*\b|\b\d+x\b|\b\d+\+?\s*(users|clients|requests|ms|seconds|hours|queries|endpoints|stars|rules|projects|apis)\b|\b\d+\+\b)", raw_text, re.I)
        metric_count = len(metric_matches)

        impact_score = min(100.0, (min(action_verb_count, 10) * 5) + (min(metric_count, 5) * 10))
        checks.append(ATSCheckDetail(
            name="Measurable Impact & Action Verbs",
            passed=action_verb_count >= 5 and metric_count >= 2,
            score=round((impact_score / 100.0) * 25.0, 1),
            max_score=25.0,
            details=f"Identified {action_verb_count} strong action verbs and {metric_count} quantified outcome metrics (e.g. percentages, scale, speedups).",
            severity="warning" if metric_count < 2 else "info"
        ))
        if metric_count < 2:
            suggestions.append("Strengthen bullet points with quantified results (e.g., 'Improved API response latency by 35%' instead of 'Worked on API optimization').")

        # Check 4: Formatting & Text Extraction Quality
        special_char_ratio = len(re.findall(r"[^\w\s.,;:()\-/@+]", raw_text)) / max(len(raw_text), 1)
        format_passed = special_char_ratio < 0.05
        format_score = max(0.0, 100.0 - (special_char_ratio * 500))
        if special_char_ratio >= 0.05:
            formatting_warnings.append("High ratio of uncommon symbols or table glyphs detected. Consider using standard UTF-8 characters and simple bullet points.")
        
        # Check text length / word count
        words = raw_text.split()
        if len(words) < 150:
            formatting_warnings.append("Resume appears unusually brief (< 150 words). May be missing relevant experience details.")
        elif len(words) > 1200:
            formatting_warnings.append("Resume word count is high (> 1200 words). Consider condensing to 1-2 pages.")

        checks.append(ATSCheckDetail(
            name="Formatting & Parsing Cleanliness",
            passed=format_passed,
            score=round((format_score / 100.0) * 20.0, 1),
            max_score=20.0,
            details=f"Text density: {len(words)} words. Non-standard symbol ratio: {special_char_ratio:.2%}.",
            severity="warning" if not format_passed else "info"
        ))

        # Check 5: Skill Consistency across sections
        # Check if skills mentioned in summary appear in experience or projects
        skills_in_exp = 0
        exp_text = profile.raw_sections.get("experience", "").lower() + " " + profile.raw_sections.get("projects", "").lower()
        for skill in profile.skills:
            if re.search(r"\b" + re.escape(skill.lower()) + r"\b", exp_text):
                skills_in_exp += 1
                evidence_items.append({
                    "skill": skill,
                    "evidence_found": True,
                    "source": "Experience / Projects",
                    "confidence": 0.95
                })
            else:
                evidence_items.append({
                    "skill": skill,
                    "evidence_found": False,
                    "source": "Skills section only (no contextual project evidence)",
                    "confidence": 0.40
                })

        consistency_ratio = (skills_in_exp / max(len(profile.skills), 1))
        consistency_score = consistency_ratio * 100.0
        checks.append(ATSCheckDetail(
            name="Skill Evidence & Context Consistency",
            passed=consistency_ratio >= 0.6,
            score=round((consistency_score / 100.0) * 20.0, 1),
            max_score=20.0,
            details=f"{skills_in_exp} of {len(profile.skills)} technical skills have supporting evidence in experience or projects.",
            severity="warning" if consistency_ratio < 0.5 else "info"
        ))
        if consistency_ratio < 0.6:
            suggestions.append("Ground your technical skills list by demonstrating how you used them in your project or experience bullet points.")

        # Optional: Job Description Matching
        job_alignment_score = None
        if job_description or required_skills:
            job_text = (job_description or "").lower()
            req_set = {s.lower() for s in (required_skills or [])}
            pref_set = {s.lower() for s in (preferred_skills or [])}

            candidate_skills_lower = {s.lower() for s in profile.skills}

            matched_req = req_set & candidate_skills_lower
            matched_pref = pref_set & candidate_skills_lower

            req_cov = len(matched_req) / max(len(req_set), 1) if req_set else 1.0
            pref_cov = len(matched_pref) / max(len(pref_set), 1) if pref_set else 1.0

            job_alignment_score = round(((req_cov * 0.75) + (pref_cov * 0.25)) * 100.0, 1)

            checks.append(ATSCheckDetail(
                name="Job Description Keyword Alignment",
                passed=req_cov >= 0.70,
                score=round(job_alignment_score, 1),
                max_score=100.0,
                details=f"Required skills matched: {len(matched_req)}/{len(req_set)}. Preferred skills matched: {len(matched_pref)}/{len(pref_set)}.",
                severity="critical" if req_cov < 0.5 else "info"
            ))

            missing_req = req_set - candidate_skills_lower
            if missing_req:
                suggestions.append(f"Target role specifically requires skills not highlighted in your resume: {', '.join(sorted(list(missing_req)))}.")

        # Compute Total Weighted Overall Score
        category_breakdown = ATSScoreBreakdown(
            section_structure_score=round(sec_score, 1),
            contact_completeness_score=round(contact_score, 1),
            content_impact_score=round(impact_score, 1),
            formatting_quality_score=round(format_score, 1),
            skill_consistency_score=round(consistency_score, 1),
            job_alignment_score=job_alignment_score,
        )

        base_score = sum(c.score for c in checks if c.name != "Job Description Keyword Alignment")
        overall_score = round(base_score, 1)

        return ComprehensiveATSReport(
            overall_score=overall_score,
            category_scores=category_breakdown,
            checks=checks,
            found_sections=found_sections,
            missing_sections=missing_sections,
            formatting_warnings=formatting_warnings,
            suggestions=suggestions,
            detected_skills=profile.skills,
            evidence_items=evidence_items,
        )


ats_validator = ATSValidatorService()
