import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.routes import matching as matching_module
from app.core.database import Base
from app.models import models  # noqa: F401 - populate Base metadata


def test_skill_evidence_uses_word_boundaries():
    assert matching_module._evidence_for("SQL", {"skills": []}, "Experienced with NoSQL") is None
    assert matching_module._evidence_for("Go", {"skills": []}, "Built services on Google Cloud") is None
    assert matching_module._evidence_for("C++", {"skills": []}, "Used C++ for systems programming") == {
        "section": "resume text (not in extracted profile)",
        "text": "Used C++ for systems programming",
    }


@pytest.mark.asyncio
async def test_resume_match_is_evidence_based_and_saved_to_database(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    resume_id = "8bca7d95-3c28-4eaf-bdd7-1b83aacbe264"
    monkeypatch.setitem(
        matching_module.RESUME_STORE,
        resume_id,
        {
            "id": resume_id,
            "filename": "reviewed-resume.txt",
            "profile_reviewed": True,
            "raw_text": "Skills: Python\nProject: Used SQL to analyze test records.",
            "profile": {
                "name": "Avery",
                "summary": "Backend engineering projects",
                "skills": ["Python"],
                "soft_skills": [],
                "experience": [],
                "projects": [{"title": "Data report", "bullets": ["Used SQL to analyze test records."]}],
                "education": [],
                "certifications": [],
            },
        },
    )
    request = matching_module.MatchCalculationRequest.model_validate({
        "resume_id": resume_id,
        "job": {
            "id": "greenhouse:456",
            "title": "Backend Engineer",
            "employer": "Example employer",
            "required_skills": ["Python", "SQL", "Kubernetes"],
            "description": "Build reliable backend services.",
            "source_name": "greenhouse",
            "original_url": "https://boards.greenhouse.io/example/jobs/456",
        },
    })

    async with sessions() as db:
        result = await matching_module.calculate_match(request, db)
        await db.commit()
        saved = await matching_module.list_saved_matches(resume_id, db)

    assert result["saved"] is True
    assert result["scoring"]["method"] == "deterministic"
    assert result["scoring"]["not_assessed_categories"] == ["preferred_skills", "experience", "location"]
    assert result["missing_required_skills"] == ["Kubernetes"]
    assert result["partial_skills"] == ["SQL"]
    assert result["match"]["skill_coverage_score"] == pytest.approx(100 / 3, abs=0.01)
    assert saved["count"] == 1
    assert saved["comparisons"][0]["job"]["title"] == "Backend Engineer"

    async with sessions() as db:
        deleted = await matching_module.delete_saved_match(result["comparison_id"], db)
        await db.commit()
    assert deleted["deleted"] is True
    await engine.dispose()


@pytest.mark.asyncio
async def test_match_requires_explicit_job_skills(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    resume_id = "3aa70a77-2f78-41d7-9f36-f0a1486341b9"
    monkeypatch.setitem(
        matching_module.RESUME_STORE,
        resume_id,
        {"id": resume_id, "profile": {"skills": []}, "raw_text": ""},
    )
    request = matching_module.MatchCalculationRequest.model_validate({
        "resume_id": resume_id,
        "job": {"title": "Engineer", "description": "A job description."},
    })
    async with sessions() as db:
        with pytest.raises(HTTPException) as error:
            await matching_module.calculate_match(request, db)

    assert error.value.status_code == 422
    assert "required skill" in error.value.detail
    await engine.dispose()


@pytest.mark.asyncio
async def test_match_requires_reviewed_resume_profile(monkeypatch):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    resume_id = "fefb8fc0-cbab-4ef8-8fd0-7cc10110e49a"
    monkeypatch.setitem(
        matching_module.RESUME_STORE,
        resume_id,
        {
            "id": resume_id,
            "profile_reviewed": False,
            "raw_text": "Skills: Python",
            "profile": {"name": "", "skills": ["Python"]},
        },
    )
    request = matching_module.MatchCalculationRequest.model_validate({
        "resume_id": resume_id,
        "job": {"title": "Engineer", "required_skills": ["Python"]},
    })
    async with sessions() as db:
        with pytest.raises(HTTPException) as error:
            await matching_module.calculate_match(request, db)

    assert error.value.status_code == 409
    assert "Review and save" in error.value.detail
    await engine.dispose()
