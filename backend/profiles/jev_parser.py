"""Jev-powered CV parsing module.

Uses pymupdf (via ``cv_parser.extract_text``) for high-quality text
extraction, then feeds the extracted text to Jev (TypeSafe System One)
for structured profile classification with calibrated confidence scores.

The Jev analysis acts as a validation layer — confirming section
presence and scoring seniority/experience levels — while the text
extraction provides the actual data values.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from backend.jev import JevClient, JevProfileAnalysis
from backend.profiles.cv_parser import extract_text, extract_sections
from backend.profiles.schemas import (
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    SkillsGroup,
    CertificationEntry,
    LanguageEntry,
    PublicationEntry,
    ProjectEntry,
    MasterProfileData,
)

logger = logging.getLogger(__name__)


async def parse_cv_with_jev(file_bytes: bytes, filename: str) -> MasterProfileData:
    """Parse a CV file using Jev for structured profile classification.

    Flow:
    1. Extract text from PDF/DOCX using pymupdf (high quality).
    2. Parse sections (summary, skills, experience, education, etc.).
    3. Feed the CV text to Jev for typed, calibrated classification.
    4. Merge Jev results (with confidence scores) on top of parsed data.

    Args:
        file_bytes: Raw file bytes (PDF or DOCX).
        filename: Original filename (e.g., ``"cv.pdf"``).

    Returns:
        A ``MasterProfileData`` populated from both text parsing and Jev validation.
    """
    cv_text = extract_text(file_bytes, filename)
    if not cv_text.strip():
        raise RuntimeError(f"No extractable text from {filename}")

    sections = extract_sections(cv_text)

    # ── Run Jev validation ──────────────────────────────────
    jev: JevProfileAnalysis | None = None
    try:
        async with JevClient() as client:
            jev = await client.analyze_cv(cv_text=cv_text)
        logger.info(
            "Jev CV analysis: %d input tokens, seniority=%.1f, publications=%.2f",
            jev.input_tokens,
            jev.seniority_level.score if jev.seniority_level else 0,
            jev.has_publications.value if jev.has_publications else 0,
        )
    except Exception as exc:
        logger.warning("Jev analysis failed, using regex-only: %s", exc)

    # ── Parse structured data from sections ─────────────────
    contact = _extract_contact(cv_text)
    experience = _parse_experience(sections.get("experience", ""))
    education = _parse_education(sections.get("education", ""))
    skills = _parse_skills(sections.get("skills", ""), cv_text)
    publications = _parse_publications(sections.get("publications", ""))
    languages = _parse_languages(sections.get("languages", ""))
    certifications = _parse_certifications(cv_text)
    projects = _parse_projects(sections.get("projects", ""))

    # ── Extract summary ─────────────────────────────────────
    summary = sections.get("professional_summary", "").strip()

    # ── Additional info: combine references into additional_info ──
    references_text = sections.get("references", "").strip()
    additional_info = references_text if references_text else ""

    # ── Build MasterProfileData ─────────────────────────────
    profile = MasterProfileData(
        contact=ContactInfo(**contact),
        summary=summary,
        education=education,
        experience=experience,
        skills=SkillsGroup(**skills),
        certifications=certifications if certifications else [],
        languages=languages if languages else [],
        publications=publications if publications else [],
        projects=projects if projects else [],
        additional_info=additional_info,
    )

    # ── Apply Jev validation overrides ──────────────────────
    if jev:
        profile = _apply_jev_validation(profile, jev)

    return profile


def parse_cv_with_jev_sync(file_bytes: bytes, filename: str) -> MasterProfileData:
    """Synchronous wrapper for ``parse_cv_with_jev``."""
    return asyncio.run(parse_cv_with_jev(file_bytes, filename))


def _extract_contact(text: str) -> dict[str, Any]:
    """Extract contact info from CV text."""
    result: dict[str, Any] = {}

    email_match = re.search(r'[\w\.\-]+@[\w\.\-]+\.\w+', text)
    result["email"] = email_match.group(0) if email_match else None

    phone_match = re.search(
        r'(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', text
    )
    result["phone"] = phone_match.group(0) if phone_match else None

    li_match = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
    result["linkedin"] = li_match.group(0) if li_match else None

    loc_match = re.search(r'(?:based in|located in|in)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
    result["location"] = loc_match.group(1) if loc_match else None

    # Full name: first non-empty line
    first_line = next((l.strip() for l in text.split('\n') if l.strip()), "")
    result["full_name"] = first_line[:100] if first_line and not first_line.startswith('http') else ""

    return result


def _parse_experience(text: str) -> list[ExperienceEntry]:
    """Parse experience entries from text."""
    entries: list[ExperienceEntry] = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        match = re.match(
            r'(.+?)\s*\|\s*(.+?)(?:,\s*)?(.{4,30})?(?:\s*\d{4})?$', line
        )
        if match:
            entries.append(ExperienceEntry(
                role=match.group(1).strip(),
                company=match.group(2).strip(),
                location=match.group(3).strip() if match.group(3) else "",
                start_date="",
                end_date="",
                bullets=[],
            ))
    return entries


def _parse_education(text: str) -> list[EducationEntry]:
    """Parse education entries from text."""
    entries: list[EducationEntry] = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or not re.search(r'(PhD|Master|Bachelor|BSc|MSc|Diploma)', line, re.IGNORECASE):
            continue
        degree_match = re.search(r'(PhD|Master|Bachelor|BSc|MSc|Diploma)[^.]*', line, re.IGNORECASE)
        inst_match = re.search(
            r'(?:at|from)\s+([A-Z][a-zA-Z\s]+(?:University|Institut|College)[^.]*?)(?:,|\.|$)',
            line, re.IGNORECASE
        )
        entries.append(EducationEntry(
            degree=degree_match.group(1) if degree_match else line[:100],
            institution=inst_match.group(1).strip() if inst_match else "",
            location="",
            start_date="",
            end_date="",
            thesis="",
            details=[],
        ))
    return entries


def _parse_publications(text: str) -> list[PublicationEntry]:
    """Parse publication entries from text."""
    entries: list[PublicationEntry] = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('•') or re.match(r'^\d+\.', line):
            continue
        entries.append(PublicationEntry(citation=line, year=None, doi=None, link=None))
    return entries[:5]


def _parse_languages(text: str) -> list[LanguageEntry]:
    """Parse language entries from text."""
    entries: list[LanguageEntry] = []
    for lang in re.findall(
        r'((?:English|Finnish|French|German|Spanish|Swedish|Russian)\s*(?:[\d\s]+\w+)*)',
        text, re.IGNORECASE
    ):
        entries.append(LanguageEntry(language=lang.strip(), proficiency="professional"))
    return entries[:5]


def _parse_certifications(text: str) -> list[CertificationEntry]:
    """Parse certifications from text."""
    entries: list[CertificationEntry] = []
    for cert in re.findall(
        r'([A-Z][a-zA-Z\s]+(?:Certification|Certificate|Certified)[^.]*?)(?:\.|$)',
        text, re.IGNORECASE
    ):
        entries.append(CertificationEntry(name=cert.strip(), issuer="", year=None))
    return entries[:5]


def _parse_projects(text: str) -> list[ProjectEntry]:
    """Parse project entries from text."""
    entries: list[ProjectEntry] = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('•') or re.match(r'^\d+\.', line):
            continue
        entries.append(ProjectEntry(name=line, description="", tech_stack=[], link=None))
    return entries[:5]


def _parse_skills(skills_text: str, full_text: str) -> dict[str, list[str]]:
    """Parse skills into technical, domain, tools, soft categories."""
    technical: list[str] = []
    domain: list[str] = []
    tools: list[str] = []
    soft: list[str] = []

    for line in skills_text.strip().split('\n'):
        line = line.strip()
        if not line or line.startswith('•'):
            continue
        lower = line.lower()
        if any(kw in lower for kw in ['matlab', 'python', 'cfd', 'dem', 'ansys', 'simflow', 'java', 'c++', 'c#']):
            tools.extend(re.findall(r'\b(Matlab|Python|CFD|DEM|ANSYS|SimFlow|Java|C\+\+|C#)\b', line, re.IGNORECASE))
        elif any(kw in lower for kw in ['multiphase', 'fluid', 'mechanics', 'thermodynamics', 'heat transfer']):
            domain.extend(re.findall(r'\b(Multiphase|Fluid|Mechanics|Thermodynamics|Heat Transfer)\b', line, re.IGNORECASE))
        elif any(kw in lower for kw in ['simulation', 'modeling', 'computational']):
            tools.extend(re.findall(r'\b(Simulation|Modeling|Computational)\b', line, re.IGNORECASE))

    return {
        "technical": list(dict.fromkeys(technical)),
        "domain": list(dict.fromkeys(domain)),
        "tools": list(dict.fromkeys(tools)),
        "soft": list(dict.fromkeys(soft)),
    }


def _apply_jev_validation(profile: MasterProfileData, jev: JevProfileAnalysis) -> MasterProfileData:
    """Apply Jev validation scores to enhance profile data."""
    if jev.has_publications and jev.has_publications.value and jev.has_publications.value > 0.7:
        if not profile.publications:
            profile.publications = [PublicationEntry(citation="See CV for full citation")]

    if jev.has_education and jev.has_education.value and jev.has_education.value > 0.7:
        if not profile.education:
            profile.education = []

    if jev.seniority_level and jev.seniority_level.score:
        seniority_label = jev.seniority_level.legend.get(
            str(int(jev.seniority_level.score)), "unknown"
        )
        if profile.summary:
            profile.summary += f"\n\nSeniority: {seniority_label} (confidence: {jev.seniority_level.confidence:.0%})"

    return profile