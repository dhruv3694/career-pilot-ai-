"""Temporary, synthetic documents exercise the supported resume parsers."""

import pymupdf as fitz
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app.api.routes import resumes as resumes_module
from app.services.resume.parser import ResumeParser


RESUME_TEXT = """Avery Example
Professional Summary
Software developer with experience building reliable web applications.
Work Experience
- Developed an internal Python service for data processing.
Education
- Bachelor of Science, Example University, 2022
Technical Skills
- Python, SQL, Git
"""


@pytest.fixture
def parser():
    return ResumeParser()


def write_pdf(path, pages):
    document = fitz.open()
    for text in pages:
        page = document.new_page()
        page.insert_text((72, 72), text)
    document.save(path)
    document.close()
    return path


def write_docx(path, text=RESUME_TEXT):
    document = Document()
    for line in text.splitlines():
        document.add_paragraph(line)
    document.save(path)
    return path


def write_scanned_pdf(path, image_path):
    pixmap = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 40, 40), 0)
    pixmap.clear_with(230)
    pixmap.save(image_path)
    document = fitz.open()
    page = document.new_page()
    page.insert_image(page.rect, filename=str(image_path))
    document.save(path)
    document.close()
    return path


def test_parses_text_pdf_and_multiple_pages(parser, tmp_path):
    path = write_pdf(tmp_path / "resume.pdf", [RESUME_TEXT[:150], RESUME_TEXT[150:]])

    result = parser.parse(str(path), ".pdf")

    assert result.status == "success"
    assert result.page_count == 2
    assert result.word_count > 20
    assert result.ocr_status == "not_needed"
    assert "Work Experience" in result.text


def test_parses_docx_with_tables_bullets_and_unicode(parser, tmp_path):
    path = tmp_path / "resume.docx"
    document = Document()
    document.add_paragraph("Avery Example")
    document.add_paragraph("Professional Summary")
    document.add_paragraph("Engineer with experience developing software for users.")
    document.add_paragraph("Education")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "B.Sc. – Computer Science"
    table.cell(0, 1).text = "Université Example"
    document.add_paragraph("Work Experience")
    document.add_paragraph("• Built a tool used by five teams.")
    document.save(path)

    result = parser.parse(str(path), ".docx")

    assert result.status == "success"
    assert "B.Sc. – Computer Science | Université Example" in result.text
    assert "• Built a tool used by five teams." in result.text
    assert result.metadata["table_count"] == 1


def test_parses_utf8_text_and_normalizes_line_endings(parser, tmp_path):
    path = tmp_path / "resume.txt"
    path.write_text(RESUME_TEXT.replace("\n", "\r\n") + "Avery’s portfolio.", encoding="utf-8")

    result = parser.parse(str(path), "text/plain")

    assert result.status == "success"
    assert "\r" not in result.text
    assert "Avery’s portfolio." in result.text


def test_parses_utf16_text_file(parser, tmp_path):
    path = tmp_path / "resume_utf16.txt"
    path.write_text(RESUME_TEXT + "Avery’s portfolio.", encoding="utf-16")

    result = parser.parse(str(path), ".txt")

    assert result.status == "success"
    assert "Avery’s portfolio." in result.text


@pytest.mark.parametrize("encoding", ["utf-32", "utf-32-le", "utf-32-be"])
def test_parses_utf32_text_file(parser, tmp_path, encoding):
    path = tmp_path / "resume_utf32.txt"
    path.write_text(RESUME_TEXT + "Avery’s portfolio.", encoding=encoding)

    result = parser.parse(str(path), ".txt")

    assert result.status == "success"
    assert "Avery’s portfolio." in result.text


def test_missing_resume_sections_do_not_fail_parsing(parser, tmp_path):
    path = tmp_path / "resume.txt"
    path.write_text(
        "Avery Example\nPython developer with several years building reliable software systems.",
        encoding="utf-8",
    )

    result = parser.parse(str(path), ".txt")

    assert result.status == "success"
    assert result.text.startswith("Avery Example")


@pytest.mark.parametrize(
    ("filename", "contents", "file_type", "message"),
    [
        ("empty.txt", b"", ".txt", "empty"),
        ("corrupted.pdf", b"%PDF-1.7 not a valid document", ".pdf", "Unable to read the PDF"),
        ("wrong_type.pdf", b"This is plain text, not a PDF.", ".pdf", "valid PDF header"),
        ("little.txt", b"Avery Example\nPython developer", ".txt", "No meaningful resume text"),
    ],
)
def test_rejects_empty_corrupt_mismatched_and_low_text_files(
    parser, tmp_path, filename, contents, file_type, message
):
    path = tmp_path / filename
    path.write_bytes(contents)

    with pytest.raises(ValueError, match=message):
        parser.parse(str(path), file_type)


def test_rejects_unsupported_file_type(parser, tmp_path):
    path = tmp_path / "resume.rtf"
    path.write_text(RESUME_TEXT, encoding="utf-8")

    with pytest.raises(ValueError, match="Unsupported file type"):
        parser.parse(str(path), ".rtf")


def test_scanned_pdf_is_reported_as_needing_ocr(parser, tmp_path):
    path = tmp_path / "scanned.pdf"
    write_scanned_pdf(path, tmp_path / "scan.png")

    result = parser.parse(str(path), ".pdf")

    assert result.status == "needs_ocr"
    assert result.is_scanned is True
    assert result.ocr_status == "not_configured"
    assert any("OCR is not configured" in warning for warning in result.warnings)


def test_rejects_blank_pdf_instead_of_reporting_ocr_needed(parser, tmp_path):
    path = tmp_path / "blank.pdf"
    document = fitz.open()
    document.new_page()
    document.save(path)
    document.close()

    with pytest.raises(ValueError, match="No meaningful resume text"):
        parser.parse(str(path), ".pdf")


def test_rejects_corrupt_docx(parser, tmp_path):
    path = tmp_path / "corrupt.docx"
    path.write_bytes(b"not a zip archive")

    with pytest.raises(ValueError, match="DOCX document is corrupted"):
        parser.parse(str(path), ".docx")


@pytest.fixture
def api_client(monkeypatch):
    from app import main

    async def skip_database_init():
        return None

    monkeypatch.setattr(main, "init_db", skip_database_init)
    with TestClient(main.app) as client:
        yield client


def test_upload_api_returns_parsed_profile_and_cleans_temporary_file(api_client, tmp_path):
    path = write_docx(tmp_path / "candidate.docx")
    before = set(resumes_module.os.listdir(resumes_module.UPLOAD_DIR))
    with path.open("rb") as document:
        response = api_client.post(
            "/api/resumes/upload",
            files={
                "file": (
                    r"..\candidate.docx",
                    document,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    after = set(resumes_module.os.listdir(resumes_module.UPLOAD_DIR))

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "success"
    assert payload["filename"] == "candidate.docx"
    assert payload["profile"]["name"] == "Avery Example"
    assert payload["page_count"] >= 1
    assert "ats_report" in payload
    assert after == before

    fetched = api_client.get(f"/api/resumes/{payload['resume_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["profile"]["name"] == "Avery Example"

    comparison = api_client.post(
        "/api/resumes/analyze-against-job",
        json={
            "resume_id": payload["resume_id"],
            "job_description": "Python developer with SQL experience.",
            "required_skills": ["Python", "SQL"],
        },
    )
    assert comparison.status_code == 200
    assert comparison.json()["ats_report"]["category_scores"]["job_alignment_score"] is not None


@pytest.mark.parametrize(
    ("filename", "contents", "content_type", "expected_status", "message"),
    [
        ("resume.pdf", b"not a PDF", "application/pdf", 422, "valid PDF header"),
        ("resume.docx", b"plain text", "text/plain", 400, "does not match"),
        ("resume.rtf", b"document", "text/plain", 400, "Unsupported file type"),
        ("resume.txt", b"", "text/plain", 422, "empty"),
    ],
)
def test_upload_api_rejects_invalid_documents(
    api_client, filename, contents, content_type, expected_status, message
):
    response = api_client.post(
        "/api/resumes/upload",
        files={"file": (filename, contents, content_type)},
    )

    assert response.status_code == expected_status
    assert message.lower() in response.json()["detail"].lower()


def test_upload_api_does_not_claim_success_for_scanned_pdf(api_client, tmp_path):
    path = tmp_path / "scanned.pdf"
    write_scanned_pdf(path, tmp_path / "scan.png")

    with path.open("rb") as pdf:
        response = api_client.post(
            "/api/resumes/upload",
            files={"file": ("scanned.pdf", pdf, "application/pdf")},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "needs_ocr"
    assert response.json()["ocr_status"] == "not_configured"
    assert "profile" not in response.json()
