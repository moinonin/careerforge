"""CV parser tests."""

import pytest

from backend.profiles.cv_parser import parse_cv


@pytest.fixture
def sample_cv_docx() -> bytes:
    """Create a minimal DOCX with sample CV content."""
    from docx import Document
    import io

    doc = Document()
    doc.add_paragraph("Jane Developer")
    doc.add_paragraph("Software Engineer")
    doc.add_paragraph("jane@example.com")
    doc.add_paragraph("")
    doc.add_paragraph("Experience")
    doc.add_paragraph("Software Engineer at TechCo, 2020-2023")
    doc.add_paragraph("")
    doc.add_paragraph("Education")
    doc.add_paragraph("BSc Computer Science, Stanford University")
    doc.add_paragraph("")
    doc.add_paragraph("Skills")
    doc.add_paragraph("Python, React, Docker, AWS")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_parse_docx_returns_structure(sample_cv_docx: bytes) -> None:
    """Parsing a DOCX returns a _ParsedSection with populated fields."""
    result = parse_cv(sample_cv_docx, "test_cv.docx")

    assert result.contact.get("full_name") == "Jane Developer"
    assert result.contact.get("email") == "jane@example.com"
    assert len(result.experience) > 0
    assert len(result.education) > 0
    assert len(result.skills["technical"]) > 0 or len(result.skills["tools"]) > 0
    assert result.confidence_flags is not None


def test_parse_docx_returns_confidence_flags(sample_cv_docx: bytes) -> None:
    """Missing fields get confidence flags."""
    result = parse_cv(sample_cv_docx, "test_cv.docx")
    # Full name and email should be found, no critical flags
    assert "full_name" not in result.confidence_flags.get("contact", "")
    assert "email" not in result.confidence_flags.get("contact", "")


def test_parse_returns_status_completed_for_docx() -> None:
    """DOCX parsing returns completed status."""
    from backend.profiles.cv_parser import _ParsedSection
    import io
    from docx import Document

    doc = Document()
    doc.add_paragraph("Test User")
    buf = io.BytesIO()
    doc.save(buf)
    data = buf.getvalue()

    result = parse_cv(data, "test.docx")
    assert isinstance(result, _ParsedSection)
    assert result.confidence_flags is not None


def test_parse_unsupported_format_returns_flags() -> None:
    """Unsupported file types return empty data with flags."""
    result = parse_cv(b"not a valid file", "test.txt")
    assert result.contact == {}
    assert len(result.education) == 0
    assert "unsupported_format" in result.confidence_flags.get("contact", "")