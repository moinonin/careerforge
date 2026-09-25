"""CV parsing utilities.

Reads uploaded DOCX or PDF files and extracts text content that can be
mapped to a MasterProfileData structure.  Falls back gracefully when a
field cannot be identified — missing fields are left at their Pydantic
defaults so the user can fill them in via the wizard.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class _ParsedSection(BaseModel):
    """Minimal section extracted from raw CV text."""

    contact: dict[str, Any] = {}
    education: list[dict[str, Any]] = []
    experience: list[dict[str, Any]] = []
    skills: dict[str, list[str]] = {"technical": [], "domain": [], "tools": [], "soft": []}
    publications: list[dict[str, Any]] = []
    certifications: list[dict[str, Any]] = []
    languages: list[dict[str, Any]] = []
    projects: list[dict[str, Any]] = []
    confidence_flags: dict[str, str] = {}


def _extract_docx_text(file_bytes: bytes) -> str:
    """Extract plain text from a .docx file."""
    import io
    from docx import Document

    doc = Document(io.BytesIO(file_bytes))
    paragraphs = []
    for p in doc.paragraphs:
        text = p.text.strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from a .pdf file."""
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n".join(pages)


import io


def parse_cv(file_bytes: bytes, filename: str) -> _ParsedSection:
    """Parse a CV file (DOCX or PDF) and return extracted profile data.

    Parameters
    ----------
    file_bytes:
        Raw file content from the upload.
    filename:
        Original filename — used to determine file type.

    Returns
    -------
    _ParsedSection
        Extracted data with confidence flags indicating which fields
        could not be reliably parsed.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "docx":
        text = _extract_docx_text(file_bytes)
    elif ext == "pdf":
        text = _extract_pdf_text(file_bytes)
    else:
        return _ParsedSection(confidence_flags={
            "contact": "unsupported_format",
            "education": "unsupported_format",
            "experience": "unsupported_format",
            "skills": "unsupported_format",
        })

    return _parse_text(text)


def _parse_text(text: str) -> _ParsedSection:
    """Map raw CV text to structured profile sections.

    This is a heuristic-based parser — it identifies sections by
    common CV headings and extracts simple key-value pairs for
    contact information.  Complex entries (multi-line bullet points,
    nested education) are captured at a basic level.

    Returns a _ParsedSection with confidence flags for fields that
    could not be reliably identified.
    """
    lines = text.split("\n")
    result = _ParsedSection()
    flags: dict[str, str] = {}

    current_section: str | None = None
    section_buffer: list[str] = []

    # Section heading patterns (case-insensitive)
    section_patterns: dict[str, re.Pattern] = {
        "education": re.compile(r"^\s*(education|qualifications)\s*$", re.I),
        "experience": re.compile(r"^\s*(experience|work\s*history|professional\s*experience)\s*$", re.I),
        "skills": re.compile(r"^\s*(skills|technical\s*skills)\s*$", re.I),
        "publications": re.compile(r"^\s*(publications|research)\s*$", re.I),
        "certifications": re.compile(r"^\s*(certifications|certificates|licenses)\s*$", re.I),
        "languages": re.compile(r"^\s*languages\s*$", re.I),
        "projects": re.compile(r"^\s*(projects|portfolio)\s*$", re.I),
    }

    def _flush_section() -> None:
        """Process the accumulated lines for the current section."""
        nonlocal current_section, section_buffer
        if not current_section or not section_buffer:
            return
        _process_section(current_section, section_buffer, result, flags)
        section_buffer = []

    for line in lines:
        stripped = line.strip()
        # Check if this line starts a new section
        matched = False
        for section_name, pattern in section_patterns.items():
            if pattern.match(stripped):
                _flush_section()
                current_section = section_name
                matched = True
                break
        if matched:
            continue
        if current_section:
            section_buffer.append(stripped)

    _flush_section()

    # Extract contact info from any line that looks like email/phone/linkedin
    for line in lines:
        email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", line)
        if email_match and not result.contact.get("email"):
            result.contact["email"] = email_match.group(0)
            flags.setdefault("contact", "partial")

        phone_match = re.search(r"\+?[\d\s\-\(\)]{7,20}", line)
        if phone_match and not result.contact.get("phone") and len(phone_match.group(0).strip()) > 7:
            result.contact["phone"] = phone_match.group(0).strip()

        linkedin_match = re.search(r"(linkedin\.com/in/[A-Za-z0-9_-]+)", line, re.I)
        if linkedin_match and not result.contact.get("linkedin"):
            result.contact["linkedin"] = linkedin_match.group(1)

    # Simple name extraction — look for a single long line at the top
    # that doesn't contain @ or digits and isn't a section header
    for line in lines[:20]:
        stripped = line.strip()
        if (stripped and len(stripped) > 2 and len(stripped) < 100
                and "@" not in stripped and not re.match(r"^\d+$", stripped)
                and not any(p.match(stripped) for p in section_patterns.values())
                and not result.contact.get("full_name")):
            result.contact["full_name"] = stripped
            flags.setdefault("contact", "partial")
            break

    # Compute confidence flags for missing critical sections
    if not result.contact.get("full_name"):
        flags["contact"] = "missing_name"
    if not result.education:
        flags["education"] = "missing"
    if not result.experience:
        flags["experience"] = "missing"
    if not result.skills["technical"] and not result.skills["domain"]:
        flags["skills"] = "missing"

    result.confidence_flags = flags
    return result


def _process_section(
    section_name: str,
    lines: list[str],
    result: _ParsedSection,
    flags: dict[str, str],
) -> None:
    """Parse lines belonging to a single CV section."""
    if section_name == "education":
        for line in lines:
            # Look for degree patterns: "MBA, Stanford, 2020" or "BSc Computer Science"
            parts = [p.strip() for p in line.split(",") if p.strip()]
            if parts:
                entry: dict[str, Any] = {"degree": parts[0], "institution": "", "start_date": "", "end_date": ""}
                if len(parts) >= 2:
                    entry["institution"] = parts[1]
                result.education.append(entry)

    elif section_name == "experience":
        for line in lines:
            # Look for role/company patterns: "Software Engineer at Google, 2020-2022"
            parts = [p.strip() for p in re.split(r"[,;]", line) if p.strip()]
            if parts:
                entry: dict[str, Any] = {"role": parts[0], "company": "", "location": "", "start_date": "", "end_date": "", "bullets": []}
                if len(parts) >= 2:
                    entry["company"] = parts[1]
                result.experience.append(entry)

    elif section_name == "skills":
        for line in lines:
            # Split by commas or bullet markers
            items = re.split(r"[,●•▪]\s*", line)
            for item in items:
                item = item.strip()
                if item and len(item) < 100:
                    # Categorize: long words are tools, short words are skills
                    if len(item) <= 3 and item.isalpha():
                        result.skills["soft"].append(item)
                    elif item.lower() in ("python", "java", "go", "rust", "react", "node", "docker", "k8s", "aws", "gcp"):
                        result.skills["tools"].append(item)
                    else:
                        result.skills["technical"].append(item)

    elif section_name == "publications":
        for line in lines:
            if line.strip():
                result.publications.append({"citation": line.strip(), "year": None})

    elif section_name == "certifications":
        for line in lines:
            if line.strip():
                result.certifications.append({"name": line.strip(), "issuer": "", "date": ""})

    elif section_name == "languages":
        for line in lines:
            if line.strip():
                result.languages.append({"language": line.strip(), "proficiency": ""})

    elif section_name == "projects":
        for line in lines:
            if line.strip():
                result.projects.append({"title": line.strip(), "description": ""})


# ── pymupdf-based extraction (better quality) ──────────────────────────

def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from a PDF or DOCX file using pymupdf (preferred).

    pymupdf preserves section headers and multi-column layouts much better
    than pypdf. Falls back to pypdf if pymupdf is not available.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return _extract_pdf_pymupdf(file_bytes)
    elif ext == "docx":
        return _extract_docx(file_bytes)
    return ""


def _extract_pdf_pymupdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pymupdf (best quality)."""
    try:
        import pymupdf
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text)
        doc.close()
        return "\n\n".join(pages)
    except ImportError:
        logger.warning("pymupdf not available, falling back to pypdf")
        return _extract_pdf_pypdf(file_bytes)


def _extract_pdf_pypdf(file_bytes: bytes) -> str:
    """Extract text from PDF using pypdf (fallback)."""
    from pypdf import PdfReader
    import io
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)
    return "\n\n".join(pages)


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX."""
    from docx import Document
    import io
    doc = Document(io.BytesIO(file_bytes))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    return "\n".join(paragraphs)


def extract_sections(text: str) -> dict[str, Any]:
    """Parse extracted text into section-based structure."""
    section_markers = [
        ("professional_summary", ["PROFESSIONAL SUMMARY", "PROFILE", "SUMMARY"]),
        ("skills", ["CORE TECHNICAL COMPETENCIES", "SKILLS", "TECHNICAL SKILLS"]),
        ("experience", ["PROFESSIONAL EXPERIENCE", "WORK EXPERIENCE"]),
        ("education", ["EDUCATION", "ACADEMIC BACKGROUND"]),
        ("publications", ["PUBLICATIONS", "PEER-REVIEWED PUBLICATIONS"]),
        ("languages", ["LANGUAGES", "LANGUAGES & PROFESSIONAL REFERENCES"]),
        ("references", ["REFERENCES", "PROFESSIONAL REFERENCES"]),
        ("projects", ["PROJECTS", "PROJECT RESEARCH"]),
    ]

    sections: dict[str, str] = {}
    current_section: str | None = None

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        found = False
        for section_name, markers in section_markers:
            if upper == markers[0] or any(upper.startswith(m) for m in markers):
                current_section = section_name
                sections[section_name] = ""
                found = True
                break
        if not found and current_section:
            sections[current_section] += stripped + "\n"

    return sections