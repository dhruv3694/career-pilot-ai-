"""
Unit tests for deterministic job-candidate matching and career roadmap generation.
"""

import pytest
from app.services.matching.matcher import JobMatcher
from app.services.career.roadmap import CareerRoadmapService


def test_job_matcher_deterministic_scoring():
    matcher = JobMatcher()
    candidate = {
        "skills": ["Python", "FastAPI", "Docker", "SQL", "Git"],
        "experience": [{"title": "Backend Intern", "years": 1.0}],
        "summary": "Backend Software Developer",
        "location_preferences": {"preferred_locations": ["Remote"], "open_to_remote": True},
    }

    job_high_fit = {
        "title": "Backend Software Developer",
        "required_skills": ["Python", "FastAPI", "SQL"],
        "preferred_skills": ["Docker", "Kubernetes"],
        "requirements": {"min_years": 0.5},
        "location": "Remote",
        "work_mode": "remote",
        "description": "Building backend APIs with Python and FastAPI.",
    }

    result = matcher.match(candidate, job_high_fit)
    assert result.overall_score >= 80.0
    assert "python" in result.matched_skills or "Python" in result.matched_skills
    assert result.skill_coverage_score == 100.0


def test_career_roadmap_generation():
    service = CareerRoadmapService()
    roadmap = service.generate_roadmap(
        current_skills=["Python", "SQL"],
        target_role="Data Scientist",
        skill_gaps=["Machine Learning", "Statistics"],
    )

    assert "milestones" in roadmap
    assert len(roadmap["milestones"]) >= 2
    assert roadmap["estimated_total_weeks"] > 0
    # Milestones should include resources
    assert len(roadmap["milestones"][0]["resources"]) > 0

