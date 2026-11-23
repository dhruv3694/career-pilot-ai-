"""
Unit tests for ATS-style resume validation and structured extraction.
"""

import pytest
from app.services.resume.ats import ats_validator, ExtractedProfile, ComprehensiveATSReport


SAMPLE_RESUME = """
Dhruv Patel
Email: dhruv.patel@example.com | Phone: +91 9876543210
LinkedIn: https://linkedin.com/in/dhruvpatel-dev | GitHub: https://github.com/dhruvpatel

PROFESSIONAL SUMMARY
Results-driven software engineer with experience building scalable backend microservices, REST APIs, and automated pipelines.

TECHNICAL SKILLS
Languages & Frameworks: Python, JavaScript, TypeScript, FastAPI, React, Node.js, SQL
Databases & Cloud: PostgreSQL, MongoDB, Redis, Docker, Git, CI/CD, Linux

WORK EXPERIENCE
Backend Developer Intern - CloudFlow Systems (Jan 2025 - Present)
- Architected and implemented 15+ REST API endpoints using FastAPI and PostgreSQL, reducing query latency by 35%.
- Deployed microservices using Docker containers and orchestrated CI/CD workflows on Linux environments.
- Optimized database indexing, improving system throughput to handle 5000+ requests per second.

EDUCATION
Bachelor of Technology in Computer Science & Engineering (2021 - 2025)
Pune Institute of Computer Technology, CGPA: 8.8/10

KEY PROJECTS
CareerPilot AI Platform
- Built multi-agent job intelligence tool with LangGraph and local vector embeddings.
- Developed real-time ATS scoring engine validating 100+ resume rules.
"""


def test_resume_structure_extraction():
    profile = ats_validator.extract_structure(SAMPLE_RESUME)
    assert "Dhruv" in profile.name
    assert profile.email == "dhruv.patel@example.com"
    assert profile.phone is not None
    assert "Python" in profile.skills
    assert "FastAPI" in profile.skills or "Fastapi" in profile.skills
    assert len(profile.experience) >= 1
    assert len(profile.education) >= 1


def test_ats_scoring_and_report_generation():
    profile = ats_validator.extract_structure(SAMPLE_RESUME)
    report = ats_validator.evaluate(SAMPLE_RESUME, profile=profile)
    assert isinstance(report, ComprehensiveATSReport)
    assert report.overall_score >= 65.0
    assert report.category_scores.section_structure_score >= 60.0
    assert report.category_scores.contact_completeness_score >= 60.0
    assert len(report.checks) >= 5
    assert "CareerPilot AI uses transparent heuristic checks" in report.disclaimer


def test_job_specific_keyword_alignment():
    profile = ats_validator.extract_structure(SAMPLE_RESUME)
    report = ats_validator.evaluate(
        SAMPLE_RESUME,
        profile=profile,
        job_description="Looking for a Python Backend Developer with PostgreSQL and Docker experience.",
        required_skills=["Python", "PostgreSQL", "Docker"],
        preferred_skills=["Kubernetes", "Redis"],
    )
    assert report.category_scores.job_alignment_score is not None
    assert report.category_scores.job_alignment_score >= 75.0
