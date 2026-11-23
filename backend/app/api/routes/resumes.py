"""
Resume Intelligence and ATS API Router.
Handles resume upload, parsing, deterministic ATS assessment, LLM review,
candidate profile editing, and document export.
"""

from __future__ import annotations

import io
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.resume.parser import ResumeParser
from app.services.resume.ats import ats_validator, ComprehensiveATSReport, ExtractedProfile
from app.services.resume.analyzer import ResumeAnalyzer
from app.memory.memory_manager import memory_manager

router = APIRouter(prefix="/resumes", tags=["Resumes & ATS"])

parser = ResumeParser()
analyzer = ResumeAnalyzer()

# In-memory resume store for session
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# In-memory document store
RESUME_STORE: Dict[str, Dict[str, Any]] = {}


class ResumeTextPayload(BaseModel):
    raw_text: str = Field(..., min_length=20)
    filename: Optional[str] = "pasted_resume.txt"
    job_description: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)


class AnalyzeAgainstJobRequest(BaseModel):
    resume_id: str
    job_description: str
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)


class TailorApplicationRequest(BaseModel):
    resume_id: str
    job_title: str
    employer: Optional[str] = None
    job_description: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)


@router.post("/tailor-application")
async def tailor_application(req: TailorApplicationRequest):
    """Generate role-tailored resume bullets and cover letter without heavy local models."""
    if req.resume_id not in RESUME_STORE:
        raise HTTPException(status_code=404, detail="Resume not found in current session.")
    
    record = RESUME_STORE[req.resume_id]
    profile = record.get("profile", {})
    
    result = await analyzer.generate_tailored_application(
        profile=profile,
        job_title=req.job_title,
        employer=req.employer,
        job_description=req.job_description,
        required_skills=req.required_skills,
    )
    return {"status": "success", "tailored": result}


@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Upload resume document (PDF, DOCX, TXT) and run automated extraction."""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in parser.supported_extensions or ext not in settings.allowed_upload_types_list:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported types: {', '.join(sorted(parser.supported_extensions))}",
        )

    allowed_content_types = {
        ".pdf": {"application/pdf", "application/octet-stream"},
        ".docx": {
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/octet-stream",
        },
        ".txt": {"text/plain", "application/octet-stream"},
    }
    content_type = (file.content_type or "application/octet-stream").lower()
    if content_type not in allowed_content_types[ext]:
        raise HTTPException(
            status_code=400,
            detail=f"File content type '{content_type}' does not match the {ext} extension.",
        )

    content = await file.read(settings.max_upload_size_bytes + 1)
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    if not content:
        raise HTTPException(status_code=422, detail="The uploaded document is empty.")

    resume_id = str(uuid.uuid4())
    safe_filename = Path(file.filename or f"resume{ext}").name
    save_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=ext, prefix="resume-", dir=UPLOAD_DIR, delete=False
        ) as temp_file:
            temp_file.write(content)
            save_path = temp_file.name
        parse_result = parser.parse(save_path, ext)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        if save_path and os.path.exists(save_path):
            os.unlink(save_path)

    if parse_result.status == "needs_ocr":
        return {
            "status": parse_result.status,
            "filename": safe_filename,
            "raw_text": parse_result.text,
            "quality_score": parse_result.quality_score,
            "is_scanned": parse_result.is_scanned,
            "ocr_status": parse_result.ocr_status,
            "warnings": parse_result.warnings,
            "next_steps": [
                "Upload a text-based PDF or DOCX, or configure an OCR engine to process scanned PDFs."
            ],
        }

    profile = ats_validator.extract_structure(parse_result.text)
    ats_report = ats_validator.evaluate(parse_result.text, profile=profile)

    record = {
        "id": resume_id,
        "filename": safe_filename,
        "file_type": ext,
        "file_size": len(content),
        "raw_text": parse_result.text,
        "quality_score": parse_result.quality_score,
        "is_scanned": parse_result.is_scanned,
        "ocr_status": parse_result.ocr_status,
        "warnings": parse_result.warnings,
        "word_count": parse_result.word_count,
        "page_count": parse_result.page_count,
        "detected_sections": ats_report.found_sections,
        "profile": profile.model_dump(),
        "profile_reviewed": False,
        "ats_report": ats_report.model_dump(),
        "llm_review": None,
    }
    RESUME_STORE[resume_id] = record

    # Index in vector store for evidence retrieval
    memory_manager.index_resume_for_evidence(
        resume_id=resume_id,
        candidate_name=profile.name,
        text=parse_result.text,
    )

    return {
        "status": "success",
        "resume_id": resume_id,
        "filename": safe_filename,
        "raw_text": parse_result.text,
        "quality_score": parse_result.quality_score,
        "is_scanned": parse_result.is_scanned,
        "ocr_status": parse_result.ocr_status,
        "warnings": parse_result.warnings,
        "next_steps": [],
        "word_count": parse_result.word_count,
        "page_count": parse_result.page_count,
        "detected_sections": ats_report.found_sections,
        "profile": profile.model_dump(),
        "profile_reviewed": False,
        "ats_report": ats_report.model_dump(),
    }


@router.post("/parse-text")
async def parse_raw_text(payload: ResumeTextPayload):
    """Directly analyze pasted resume text without uploading a file."""
    resume_id = str(uuid.uuid4())
    profile = ats_validator.extract_structure(payload.raw_text)
    ats_report = ats_validator.evaluate(
        payload.raw_text,
        profile=profile,
        job_description=payload.job_description,
    )

    record = {
        "id": resume_id,
        "filename": payload.filename,
        "file_type": ".txt",
        "file_size": len(payload.raw_text.encode("utf-8")),
        "raw_text": payload.raw_text,
        "quality_score": 1.0,
        "is_scanned": False,
        "warnings": [],
        "word_count": len(payload.raw_text.split()),
        "page_count": 1,
        "profile": profile.model_dump(),
        "profile_reviewed": False,
        "ats_report": ats_report.model_dump(),
        "llm_review": None,
    }
    RESUME_STORE[resume_id] = record

    memory_manager.index_resume_for_evidence(
        resume_id=resume_id,
        candidate_name=profile.name,
        text=payload.raw_text,
    )

    return {
        "status": "success",
        "resume_id": resume_id,
        "profile": profile.model_dump(),
        "ats_report": ats_report.model_dump(),
    }


@router.get("/{resume_id}")
async def get_resume(resume_id: str):
    """Retrieve resume assessment, extracted profile, and ATS report."""
    if resume_id not in RESUME_STORE:
        raise HTTPException(status_code=404, detail="Resume not found")
    return RESUME_STORE[resume_id]


@router.put("/{resume_id}/profile")
async def update_extracted_profile(resume_id: str, update: ProfileUpdateRequest):
    """Allow user to review and correct extracted profile fields."""
    if resume_id not in RESUME_STORE:
        raise HTTPException(status_code=404, detail="Resume not found")

    record = RESUME_STORE[resume_id]
    record["profile"].update(update.model_dump())
    record["profile_reviewed"] = True

    # Re-run ATS scoring with updated candidate fields
    p_obj = ExtractedProfile(**record["profile"])
    new_ats = ats_validator.evaluate(record["raw_text"], profile=p_obj)
    record["ats_report"] = new_ats.model_dump()

    return {
        "status": "success",
        "message": "Candidate profile updated and ATS score re-evaluated",
        "profile": record["profile"],
        "ats_report": record["ats_report"],
    }


@router.post("/{resume_id}/llm-review")
async def run_llm_review(resume_id: str, job_description: Optional[str] = Form(None)):
    """Run LLM-assisted bullet point suggestions and claim verification."""
    if resume_id not in RESUME_STORE:
        raise HTTPException(status_code=404, detail="Resume not found")

    record = RESUME_STORE[resume_id]
    review = await analyzer._run_llm_review(
        resume_text=record["raw_text"],
        profile=record["profile"],
        job_description=job_description,
    )
    record["llm_review"] = review
    return {
        "status": "success",
        "llm_review": review,
    }


@router.post("/analyze-against-job")
async def analyze_against_job(payload: AnalyzeAgainstJobRequest):
    """Run job-specific resume analysis against a targeted job description."""
    if payload.resume_id not in RESUME_STORE:
        raise HTTPException(status_code=404, detail="Resume not found")

    record = RESUME_STORE[payload.resume_id]
    profile = ExtractedProfile(**record["profile"])
    report = ats_validator.evaluate(
        raw_text=record["raw_text"],
        profile=profile,
        job_description=payload.job_description,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
    )
    return {
        "status": "success",
        "ats_report": report.model_dump(),
    }


@router.get("/{resume_id}/export/{format_type}")
async def export_resume(resume_id: str, format_type: str):
    """Export resume to text or formatted DOCX."""
    if resume_id not in RESUME_STORE:
        raise HTTPException(status_code=404, detail="Resume not found")

    record = RESUME_STORE[resume_id]
    profile = record["profile"]

    if format_type == "txt":
        txt_content = f"{profile.get('name', 'Candidate')}\n"
        if profile.get('email'):
            txt_content += f"Email: {profile['email']} | "
        if profile.get('phone'):
            txt_content += f"Phone: {profile['phone']}\n"
        txt_content += f"\nSUMMARY\n{profile.get('summary', '')}\n\n"
        txt_content += "SKILLS\n" + ", ".join(profile.get("skills", [])) + "\n\n"
        txt_content += "EXPERIENCE\n"
        for exp in profile.get("experience", []):
            txt_content += f"- {exp.get('title', 'Role')}\n"
            for b in exp.get("bullets", []):
                txt_content += f"  • {b}\n"

        return Response(
            content=txt_content,
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=resume_{resume_id}.txt"},
        )
    elif format_type == "docx":
        from docx import Document
        doc = Document()
        doc.add_heading(profile.get('name', 'Candidate'), level=0)
        p_contact = doc.add_paragraph()
        if profile.get('email'):
            p_contact.add_run(f"Email: {profile['email']} | ")
        if profile.get('phone'):
            p_contact.add_run(f"Phone: {profile['phone']} | ")
        if profile.get('linkedin_url'):
            p_contact.add_run(f"LinkedIn: {profile['linkedin_url']}")

        if profile.get('summary'):
            doc.add_heading("Professional Summary", level=1)
            doc.add_paragraph(profile['summary'])

        doc.add_heading("Technical Skills", level=1)
        doc.add_paragraph(", ".join(profile.get("skills", [])))

        if profile.get("experience"):
            doc.add_heading("Work Experience", level=1)
            for exp in profile["experience"]:
                doc.add_heading(exp.get("title", "Experience"), level=2)
                for b in exp.get("bullets", []):
                    doc.add_paragraph(b, style="List Bullet")

        buf = io.BytesIO()
        doc.save(buf)
        buf.seek(0)
        return Response(
            content=buf.getvalue(),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename=resume_{resume_id}.docx"},
        )
    else:
        raise HTTPException(status_code=400, detail="Supported export formats are 'txt' and 'docx'")
