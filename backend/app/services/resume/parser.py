"""
Resume Parser Service
=====================
Handles parsing of PDF, DOCX, and TXT resume files with quality scoring,
scanned PDF detection, and comprehensive metadata extraction.
"""

import codecs
import logging
import os
import re
import unicodedata
import zipfile
from pathlib import Path
from typing import Literal, Optional

import pymupdf as fitz
from docx import Document as DocxDocument
from docx.table import Table
from docx.text.paragraph import Paragraph
from pydantic import BaseModel, Field

try:
    from app.core.config import settings
except ImportError:
    from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
MIN_TEXT_LENGTH = 50  # characters – below this the document is considered empty
SCANNED_PDF_CHAR_THRESHOLD = 30  # chars per page to flag as scanned
MAX_DOCX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024


# ---------------------------------------------------------------------------
# Pydantic result model
# ---------------------------------------------------------------------------
class ParseResult(BaseModel):
    """Structured output from resume parsing."""

    status: Literal["success", "needs_ocr"] = "success"
    text: str = Field(default="", description="Extracted plain text from the resume")
    metadata: dict = Field(default_factory=dict, description="File & extraction metadata")
    quality_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Extraction quality score between 0 and 1",
    )
    is_scanned: bool = Field(
        default=False,
        description="True if the PDF appears to be a scanned image without a text layer",
    )
    ocr_status: Literal["not_applicable", "not_configured", "not_needed"] = "not_applicable"
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings generated during parsing",
    )
    page_count: int = Field(default=0, ge=0, description="Number of pages in the document")
    word_count: int = Field(default=0, ge=0, description="Word count of extracted text")


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------
class ResumeParser:
    """Parse resume files (PDF / DOCX / TXT) and return structured results."""

    supported_extensions = SUPPORTED_EXTENSIONS

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def parse(self, file_path: str, file_type: str) -> ParseResult:
        """
        Parse a resume file and return extracted text with metadata.

        Parameters
        ----------
        file_path : str
            Absolute or relative path to the resume file on disk.
        file_type : str
            MIME type or file extension (e.g. ``".pdf"``, ``"application/pdf"``).

        Returns
        -------
        ParseResult
            Structured parse output including text, quality score, and warnings.

        Raises
        ------
        FileNotFoundError
            If *file_path* does not exist.
        ValueError
            If the file type is unsupported or the file exceeds the size limit.
        """
        path = Path(file_path)

        # --- existence check ---
        if not path.exists():
            raise FileNotFoundError(f"Resume file not found: {file_path}")

        # --- size check ---
        file_size = path.stat().st_size
        max_bytes = settings.max_upload_size_bytes
        if file_size > max_bytes:
            raise ValueError(
                f"File size ({file_size:,} bytes) exceeds the maximum allowed "
                f"({max_bytes:,} bytes / {settings.MAX_UPLOAD_SIZE_MB} MB)."
            )

        # --- extension normalisation ---
        ext = self._normalise_extension(file_type, path)
        if ext not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext}'. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )

        self._validate_file(path, ext)
        logger.info("Parsing resume: %s (type=%s, size=%d bytes)", file_path, ext, file_size)

        # --- dispatch ---
        if ext == ".pdf":
            result = self._parse_pdf(file_path)
        elif ext == ".docx":
            result = self._parse_docx(file_path)
        else:
            result = self._parse_txt(file_path)

        # --- common metadata ---
        result.metadata.update(
            {
                "file_name": path.name,
                "file_size_bytes": file_size,
                "file_extension": ext,
            }
        )

        result.text = self._normalize_text(result.text)

        if result.is_scanned and len(result.text) < MIN_TEXT_LENGTH:
            result.status = "needs_ocr"
            result.ocr_status = "not_configured"
            result.warnings.append(
                "OCR is not configured. Provide a text-based PDF or configure an OCR engine to extract this scanned document."
            )
            result.metadata["ocr_status"] = result.ocr_status
            result.quality_score = 0.0
            result.word_count = 0
            return result

        if len(result.text) < MIN_TEXT_LENGTH or len(result.text.split()) < 8:
            raise ValueError(
                "No meaningful resume text could be extracted. The document may be blank, corrupted, or image-only."
            )

        if self._has_garbled_text(result.text):
            result.warnings.append(
                "Some extracted text contains unusual control or replacement characters. Review the document and correct any extraction errors."
            )

        # --- quality ---
        result.quality_score = round(self._calculate_quality(result.text), 4)
        result.word_count = len(result.text.split())
        result.metadata["ocr_status"] = result.ocr_status

        logger.info(
            "Parse complete: pages=%d, words=%d, quality=%.2f, warnings=%d",
            result.page_count,
            result.word_count,
            result.quality_score,
            len(result.warnings),
        )
        return result

    @staticmethod
    def _looks_like_unicode_text(header: bytes) -> bool:
        """Return True when a text file likely stores UTF-16/UTF-32 data."""
        if header.startswith(
            (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE, codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)
        ):
            return True
        if not b"\x00" in header:
            return False
        even_nulls = header[0::2].count(0)
        odd_nulls = header[1::2].count(0)
        sample_len = max(1, len(header) // 2)
        return even_nulls > sample_len * 0.2 or odd_nulls > sample_len * 0.2

    @staticmethod
    def _validate_file(path: Path, ext: str) -> None:
        """Reject empty files and content that does not match its declared type."""
        if path.stat().st_size == 0:
            raise ValueError("The uploaded document is empty.")

        with path.open("rb") as file:
            header = file.read(1024)

        if ext == ".pdf":
            if b"%PDF-" not in header:
                raise ValueError("The file does not contain a valid PDF header.")
        elif ext == ".docx":
            try:
                with zipfile.ZipFile(path) as archive:
                    names = set(archive.namelist())
                    if "[Content_Types].xml" not in names or "word/document.xml" not in names:
                        raise ValueError("The file is not a valid DOCX document.")
                    if sum(item.file_size for item in archive.infolist()) > MAX_DOCX_UNCOMPRESSED_BYTES:
                        raise ValueError("The DOCX document expands beyond the supported processing size.")
                    if archive.testzip() is not None:
                        raise ValueError("The DOCX document is corrupted.")
            except (zipfile.BadZipFile, OSError) as exc:
                raise ValueError("The DOCX document is corrupted or invalid.") from exc
        elif b"\x00" in header and not ResumeParser._looks_like_unicode_text(header):
            raise ValueError("The file contains binary data and cannot be read as plain text.")

    @staticmethod
    def _normalize_text(text: str) -> str:
        """Normalize Unicode and whitespace while retaining headings and bullets."""
        normalized = unicodedata.normalize("NFC", text).replace("\u00a0", " ")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in normalized.split("\n")]
        normalized = "\n".join(lines)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    # ------------------------------------------------------------------
    # PDF
    # ------------------------------------------------------------------
    def _parse_pdf(self, file_path: str) -> ParseResult:
        """Extract text from a PDF using PyMuPDF."""
        warnings: list[str] = []
        pages_text: list[str] = []
        image_count = 0

        try:
            with fitz.open(file_path) as doc:
                if doc.needs_pass:
                    raise ValueError("The PDF is password-protected. Remove the password before uploading.")
                page_count = len(doc)
                if page_count == 0:
                    raise ValueError("The PDF contains no pages.")
                for page in doc:
                    pages_text.append(page.get_text("text", sort=True) or "")
                    image_count += len(page.get_images(full=True))
        except ValueError:
            raise
        except Exception as exc:
            logger.warning("Failed to read PDF document: %s", exc)
            raise ValueError("Unable to read the PDF. Check that it is not corrupted or password-protected.") from exc

        full_text = "\n".join(pages_text)

        # Scanned-PDF detection
        is_scanned = image_count > 0 and self._detect_scanned_from_pages(pages_text, page_count)
        if is_scanned:
            warnings.append(
                "This PDF appears to be a scanned document with little or no text layer. "
                "OCR is not configured, so candidate details cannot be extracted from its images."
            )

        # Garbled text heuristic
        if full_text and self._has_garbled_text(full_text):
            warnings.append(
                "The extracted text may contain garbled or encoding-damaged characters."
            )

        return ParseResult(
            text=full_text.strip(),
            metadata={
                "parser": "pymupdf",
                "pdf_page_count": page_count,
                "embedded_image_count": image_count,
            },
            is_scanned=is_scanned,
            ocr_status="not_configured" if is_scanned else "not_needed",
            warnings=warnings,
            page_count=page_count,
        )

    # ------------------------------------------------------------------
    # DOCX
    # ------------------------------------------------------------------
    def _parse_docx(self, file_path: str) -> ParseResult:
        """Extract text from a DOCX file using python-docx."""
        warnings: list[str] = []

        try:
            doc = DocxDocument(file_path)
        except Exception as exc:
            logger.warning("Failed to read DOCX document: %s", exc)
            raise ValueError("Unable to read the DOCX. Check that the document is not corrupted.") from exc

        paragraphs: list[str] = []
        for block in doc.element.body.iterchildren():
            if block.tag.endswith("}p"):
                text = Paragraph(block, doc).text.strip()
                if text:
                    paragraphs.append(text)
            elif block.tag.endswith("}tbl"):
                table = Table(block, doc)
                for row in table.rows:
                    row_texts = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_texts:
                        paragraphs.append(" | ".join(row_texts))

        full_text = "\n".join(paragraphs)

        # Estimate page count (roughly 3000 chars per page)
        estimated_pages = max(1, len(full_text) // 3000 + (1 if len(full_text) % 3000 else 0))

        return ParseResult(
            text=full_text.strip(),
            metadata={
                "parser": "python-docx",
                "paragraph_count": len(doc.paragraphs),
                "table_count": len(doc.tables),
            },
            warnings=warnings,
            page_count=estimated_pages,
        )

    # ------------------------------------------------------------------
    # TXT
    # ------------------------------------------------------------------
    def _parse_txt(self, file_path: str) -> ParseResult:
        """Read a plain-text resume file."""
        warnings: list[str] = []

        encodings = ["utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "cp1252"]
        try:
            with open(file_path, "rb") as fh:
                sample = fh.read(1024)
            if sample.startswith((codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
                encodings = ["utf-32", "utf-16", "utf-8-sig", "cp1252"]
            elif len(sample) >= 4 and sum(
                sample[offset::4].count(0) / max(1, len(sample[offset::4])) > 0.2
                for offset in range(4)
            ) >= 3:
                nonzero_by_lane = [sum(byte != 0 for byte in sample[offset::4]) for offset in range(4)]
                utf32_encoding = "utf-32-le" if nonzero_by_lane[0] >= nonzero_by_lane[3] else "utf-32-be"
                encodings = [utf32_encoding, "utf-8-sig", "cp1252"]
            elif sample.startswith(codecs.BOM_UTF16_LE) or sample.startswith(codecs.BOM_UTF16_BE):
                encodings = ["utf-16", "utf-16-le", "utf-16-be", "utf-8-sig", "cp1252"]
            elif self._looks_like_unicode_text(sample):
                even_nulls = sample[0::2].count(0)
                odd_nulls = sample[1::2].count(0)
                utf16_encoding = "utf-16-le" if odd_nulls > even_nulls else "utf-16-be"
                encodings = [utf16_encoding, "utf-8-sig", "cp1252"]

            for encoding in encodings:
                try:
                    with open(file_path, "r", encoding=encoding) as fh:
                        full_text = fh.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise ValueError("The text file uses an unsupported character encoding.")

            if "cp1252" in encodings and encoding == "cp1252":
                warnings.append("The text file was not UTF-8/UTF-16; it was decoded using Windows-1252.")

        except OSError as exc:
            logger.warning("Failed to read text document: %s", exc)
            raise ValueError("Unable to read the text file.") from exc

        estimated_pages = max(1, len(full_text) // 3000 + (1 if len(full_text) % 3000 else 0))

        return ParseResult(
            text=full_text.strip(),
            metadata={"parser": "plaintext"},
            warnings=warnings,
            page_count=estimated_pages,
        )

    # ------------------------------------------------------------------
    # Scanned-PDF detection
    # ------------------------------------------------------------------
    def _detect_scanned(self, pdf_path: str) -> bool:
        """Return ``True`` if the PDF is likely a scanned image (no text layer)."""
        try:
            doc = fitz.open(pdf_path)
            pages_text = [doc[i].get_text("text") or "" for i in range(len(doc))]
            page_count = len(doc)
            doc.close()
            return self._detect_scanned_from_pages(pages_text, page_count)
        except Exception:
            return False

    def _detect_scanned_from_pages(
        self, pages_text: list[str], page_count: int
    ) -> bool:
        """Heuristic: if the average characters per page is below a threshold,
        the PDF is probably scanned."""
        if page_count == 0:
            return False
        total_chars = sum(len(t.strip()) for t in pages_text)
        avg_chars = total_chars / page_count
        return avg_chars < SCANNED_PDF_CHAR_THRESHOLD

    # ------------------------------------------------------------------
    # Quality scoring
    # ------------------------------------------------------------------
    def _calculate_quality(self, text: str) -> float:
        """
        Compute a quality score ∈ [0, 1] for the extracted text.

        Factors considered:
        - Length adequacy (not too short, not absurdly long)
        - Proportion of alphabetic characters
        - Presence of common resume keywords
        - Absence of garbled / high-entropy characters
        """
        if not text or not text.strip():
            return 0.0

        score = 1.0

        # --- length factor ---
        word_count = len(text.split())
        if word_count < 30:
            score *= 0.2
        elif word_count < 100:
            score *= 0.5
        elif word_count < 200:
            score *= 0.8
        elif word_count > 5000:
            score *= 0.7  # suspiciously long

        # --- alpha ratio ---
        alpha_chars = sum(1 for c in text if c.isalpha())
        total_chars = len(text)
        alpha_ratio = alpha_chars / total_chars if total_chars else 0
        if alpha_ratio < 0.4:
            score *= 0.5
        elif alpha_ratio < 0.6:
            score *= 0.8

        # --- resume keyword presence ---
        resume_keywords = {
            "experience",
            "education",
            "skills",
            "work",
            "project",
            "summary",
            "objective",
            "certification",
            "university",
            "degree",
            "bachelor",
            "master",
            "company",
            "responsibility",
            "achievement",
        }
        text_lower = text.lower()
        found_keywords = sum(1 for kw in resume_keywords if kw in text_lower)
        keyword_ratio = found_keywords / len(resume_keywords)
        if keyword_ratio < 0.05:
            score *= 0.4
        elif keyword_ratio < 0.15:
            score *= 0.7

        # --- garbled text penalty ---
        if self._has_garbled_text(text):
            score *= 0.6

        return min(max(score, 0.0), 1.0)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _normalise_extension(file_type: str, path: Path) -> str:
        """Return a normalised file extension like ``.pdf``."""
        mime_map = {
            "application/pdf": ".pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
            "text/plain": ".txt",
        }
        ft = file_type.strip().lower()
        if ft in mime_map:
            return mime_map[ft]
        if ft.startswith("."):
            return ft
        # Fall back to path suffix
        return path.suffix.lower()

    @staticmethod
    def _has_garbled_text(text: str) -> bool:
        """Heuristic check for garbled / encoding-damaged text.

        Looks for high concentration of replacement characters, control chars,
        or sequences unlikely to appear in natural language.
        """
        if not text:
            return False
        # Count suspicious characters
        suspicious = sum(
            1
            for ch in text
            if (
                ch == "\ufffd"  # replacement character
                or (ord(ch) < 32 and ch not in "\n\r\t")
                or ord(ch) > 0xFFF0
            )
        )
        ratio = suspicious / len(text) if text else 0
        return ratio > 0.02  # more than 2 % suspicious → garbled
