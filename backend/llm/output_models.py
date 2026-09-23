"""Pydantic models for LLM output validation.

These mirror CV_SCHEMA and COVER_LETTER_SCHEMA from prompts.py exactly.
They are used by the adapter's retry loop to validate LLM responses
with real nested validation and structured error messages.

Spec reference: cv-generator-saas-spec.md Section 1.3.2 (profile_data schema)
and Section 3.3 (LLM output via structured JSON).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Output models (LLM response validation) ──────────────────────────────────

class ContactOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field(..., max_length=255)
    location: str = Field(..., max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    linkedin: str | None = Field(None, max_length=500)
    website_portfolio: str | None = Field(None, max_length=500)


class SkillsOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    technical: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


class ExperienceOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str = Field(..., max_length=255)
    company: str = Field(..., max_length=255)
    location: str | None = Field(None, max_length=255)
    start_date: str | None = Field(None, max_length=50)
    end_date: str | None = Field(None, max_length=50)
    relevance_note: str | None = Field(None, max_length=500)
    bullets: list[str] = Field(default_factory=list)


class EducationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    degree: str = Field(..., max_length=255)
    institution: str = Field(..., max_length=255)
    location: str | None = Field(None, max_length=255)
    start_date: str | None = Field(None, max_length=50)
    end_date: str | None = Field(None, max_length=50)
    thesis: str | None = Field(None, max_length=500)
    details: list[str] = Field(default_factory=list)


class PublicationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    citation: str = Field(..., max_length=1000)
    year: int | None = Field(None)
    doi: str | None = Field(None, max_length=255)
    link: str | None = Field(None, max_length=500)


class CertificationOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., max_length=255)
    issuer: str | None = Field(None, max_length=255)
    year: int | None = Field(None)


class LanguageOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    language: str = Field(..., max_length=100)
    proficiency: str = Field(..., max_length=50)


class ProjectOutput(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., max_length=255)
    description: str = Field(..., max_length=2000)
    tech_stack: list[str] = Field(default_factory=list)
    link: str | None = Field(None, max_length=500)


class CVOutput(BaseModel):
    """Full CV JSON output from the LLM — validated against CV_SCHEMA."""

    model_config = ConfigDict(extra="ignore")

    summary: str = Field(..., max_length=2000)
    contact: ContactOutput
    skills: SkillsOutput
    experience: list[ExperienceOutput] = Field(default_factory=list)
    education: list[EducationOutput] = Field(default_factory=list)
    publications: list[PublicationOutput] = Field(default_factory=list)
    certifications: list[CertificationOutput] = Field(default_factory=list)
    languages: list[LanguageOutput] = Field(default_factory=list)
    projects: list[ProjectOutput] = Field(default_factory=list)
    additional_info: str | None = Field(None, max_length=2000)


class CoverLetterOutput(BaseModel):
    """Full cover letter JSON output from the LLM — validated against COVER_LETTER_SCHEMA."""

    model_config = ConfigDict(extra="ignore")

    header: str = Field(..., max_length=500)
    salutation: str = Field(..., max_length=255)
    opening: str = Field(..., max_length=2000)
    body_paragraphs: list[str] = Field(default_factory=list)
    call_to_action: str = Field(..., max_length=500)
    closing: str = Field(..., max_length=100)
    signature: str = Field(..., max_length=255)


def cv_output_from_dict(data: dict[str, Any]) -> CVOutput:
    """Validate *data* as a CVOutput. Raises pydantic.ValidationError on failure."""
    return CVOutput.model_validate(data)


def cover_letter_output_from_dict(data: dict[str, Any]) -> CoverLetterOutput:
    """Validate *data* as a CoverLetterOutput. Raises pydantic.ValidationError on failure."""
    return CoverLetterOutput.model_validate(data)
