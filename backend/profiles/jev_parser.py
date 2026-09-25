"""Jev-powered CV parsing module.

Uses ``cv_parser.py`` (pypdf/docx) to extract plain text from uploaded
files, then feeds that text to Jev (TypeSafe System One) for structured
profile classification with calibrated confidence scores.

The Jev analysis acts as a validation layer on top of the regex-based
``cv_parser`` results — confirming presence of sections and scoring
seniority/experience levels.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.jev import JevClient, JevProfileAnalysis, JevScoreAnswer
from backend.profiles.cv_parser import parse_cv as _parse_cv_file, _ParsedSection
from backend.profiles.schemas import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    SkillsGroup,
    CertificationEntry,
    LanguageEntry,
    PublicationEntry,
    MasterProfileData,
)

logger = logging.getLogger(__name__)


def _cvtext_to_master(
    parsed: _ParsedSection,
    jev: JevProfileAnalysis | None,
) -> MasterProfileData:
    """Merge Jev analysis with regex-parsed data into MasterProfileData."""
    # Contact info from regex parser (Jev now only validates presence, not values)
    contact_data: dict[str, Any] = parsed.contact
    contact = ContactInfo(**contact_data)

    # Skills from regex parser
    skills = SkillsGroup(
        technical=parsed.skills.get("technical", []),
        domain=[],
        tools=parsed.skills.get("tools", []),
        soft=parsed.skills.get("soft", []),
    )

    # Certifications from regex parser
    certifications: list[CertificationEntry] = [
        CertificationEntry(**c) for c in (parsed.certifications or [])
    ]

    # Languages from regex parser
    languages: list[LanguageEntry] = [
        LanguageEntry(**l) for l in (parsed.languages or [])
    ]

    # Education from regex parser
    education: list[EducationEntry] = [
        EducationEntry(**e) for e in (parsed.education or [])
    ]

    # Experience from regex parser
    experience: list[ExperienceEntry] = [
        ExperienceEntry(**e) for e in (parsed.experience or [])
    ]

    # Publications from regex parser
    publications: list[PublicationEntry] = [
        PublicationEntry(**p) for p in (parsed.publications or [])
    ]

    # If Jev says has_publications but regex didn't find any, add a placeholder
    if jev and jev.has_publications and jev.has_publications.value > 0.7 and not publications:
        publications = [PublicationEntry(citation="See CV for full citation")]

    # Summary
    summary = parsed.confidence_flags.get("additional_info", "")[:2000]

    # If Jev confirms seniority, add a note to summary
    if jev and jev.seniority_level:
        seniority_label = jev.seniority_level.legend.get(
            str(int(jev.seniority_level.score)), "unknown"
        )
        summary = f"{summary}\n\nSeniority level: {seniority_label} (confidence: {jev.seniority_level.confidence:.0%})".strip()

    return MasterProfileData(
        contact=contact,
        summary=summary,
        education=education,
        experience=experience,
        skills=skills,
        publications=publications,
        certifications=certifications,
        languages=languages,
    )


async def parse_cv_with_jev(
    file_bytes: bytes,
    filename: str,
    api_key: str | None = None,
) -> MasterProfileData:
    """Parse a CV file using Jev for structured profile classification.

    Flow:
    1. Extract text and structured data from PDF/DOCX using ``cv_parser``.
    2. Feed the CV text to Jev for typed, calibrated classification
       (section presence, seniority, experience level).
    3. Merge Jev results (with confidence scores) on top of regex parsing.

    Args:
        file_bytes: Raw file bytes (PDF or DOCX).
        filename: Original filename (e.g., ``"cv.pdf"``).
        api_key: Optional Jev API key override.

    Returns:
        A ``MasterProfileData`` populated from Jev's analysis.

    Raises:
        RuntimeError: If text extraction fails.
    """
    # Step 1: Extract text and parsed data from the file
    parsed: _ParsedSection = _parse_cv_file(file_bytes, filename)

    # Extract raw text for Jev
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "docx":
        from docx import Document
        import io
        doc = Document(io.BytesIO(file_bytes))
        cv_text = "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())
    elif ext == "pdf":
        from pypdf import PdfReader
        import io
        reader = PdfReader(io.BytesIO(file_bytes))
        cv_text = "\n".join(
            page.extract_text() for page in reader.pages if page.extract_text()
        )
    else:
        raise RuntimeError(f"Unsupported file format: {ext}")

    if not cv_text.strip():
        raise RuntimeError(f"No extractable text from {filename}")

    # Step 2: Feed to Jev
    jev: JevProfileAnalysis | None = None
    try:
        async with JevClient(api_key=api_key) as client:
            jev = await client.analyze_cv(cv_text=cv_text)
        logger.info(
            "Jev CV analysis: %d input tokens, %d output tokens, "
            "seniority=%.1f, experience=%.1f, publications=%.2f",
            jev.input_tokens, jev.output_tokens,
            jev.seniority_level.score if jev.seniority_level else 0,
            jev.years_experience.score if jev.years_experience else 0,
            jev.has_publications.value if jev.has_publications else 0,
        )
    except Exception as exc:
        logger.warning("Jev analysis failed, using regex-only: %s", exc)

    # Step 3: Merge into MasterProfileData
    return _cvtext_to_master(parsed, jev)


def parse_cv_with_jev_sync(
    file_bytes: bytes,
    filename: str,
    api_key: str | None = None,
) -> MasterProfileData:
    """Synchronous wrapper for ``parse_cv_with_jev``."""
    import asyncio
    return asyncio.run(parse_cv_with_jev(file_bytes, filename, api_key))