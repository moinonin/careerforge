from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ── Profile data model (validates profile_data JSONB) ────────────────────────
# Matches spec section 1.3.2 exactly.


class ContactInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    full_name: str = Field("", max_length=255)
    location: str = Field("", max_length=255)
    phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=255)
    linkedin: str | None = Field(None, max_length=500)
    website_portfolio: str | None = Field(None, max_length=500)


class EducationEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    degree: str = Field("", max_length=255)
    institution: str = Field("", max_length=255)
    location: str | None = Field(None, max_length=255)
    start_date: str = Field("", max_length=50)
    end_date: str = Field("", max_length=50)
    thesis: str | None = Field(None, max_length=500)
    details: list[str] = Field(default_factory=list)


class ExperienceEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    role: str = Field("", max_length=255)
    company: str = Field("", max_length=255)
    location: str | None = Field(None, max_length=255)
    start_date: str = Field("", max_length=50)
    end_date: str = Field("", max_length=50)
    bullets: list[str] = Field(default_factory=list)


class SkillsGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")

    technical: list[str] = Field(default_factory=list)
    domain: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    soft: list[str] = Field(default_factory=list)


class PublicationEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    citation: str = Field("", max_length=1000)
    year: int | None = Field(None)
    doi: str | None = Field(None, max_length=255)
    link: str | None = Field(None, max_length=500)


class CertificationEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field("", max_length=255)
    issuer: str = Field("", max_length=255)
    year: int | None = Field(None)


class LanguageEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    language: str = Field("", max_length=100)
    proficiency: str = Field("", max_length=50)


class ProjectEntry(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field("", max_length=255)
    description: str = Field("", max_length=2000)
    tech_stack: list[str] = Field(default_factory=list)
    link: str | None = Field(None, max_length=500)


def _empty_contact() -> ContactInfo:
    return ContactInfo(
        full_name="",
        location="",
        phone=None,
        email=None,
        linkedin=None,
        website_portfolio=None,
    )


def _empty_skills() -> SkillsGroup:
    return SkillsGroup(
        technical=[],
        domain=[],
        tools=[],
        soft=[],
    )


class MasterProfileData(BaseModel):
    """Full structured CV content — validated on every write."""

    model_config = ConfigDict(extra="ignore")

    contact: ContactInfo = Field(default_factory=_empty_contact)
    summary: str = Field("", max_length=2000)
    education: list[EducationEntry] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    skills: SkillsGroup = Field(default_factory=_empty_skills)
    publications: list[PublicationEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    additional_info: str = Field("", max_length=2000)


# ── API request/response schemas ─────────────────────────────────────────────


class ProfileCreateRequest(BaseModel):
    title: str = Field(default="Default Master Profile", min_length=1, max_length=255)
    profile_data: MasterProfileData


class ProfileUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    profile_data: MasterProfileData | None = None
    is_default: bool | None = None
    is_draft: bool | None = None


class ProfileSectionPatchRequest(BaseModel):
    """Partial update for a single section of the profile."""

    model_config = ConfigDict(extra="ignore")

    contact: ContactInfo | None = None
    summary: str | None = None
    education: list[EducationEntry] | None = None
    experience: list[ExperienceEntry] | None = None
    skills: SkillsGroup | None = None
    publications: list[PublicationEntry] | None = None
    certifications: list[CertificationEntry] | None = None
    languages: list[LanguageEntry] | None = None
    projects: list[ProjectEntry] | None = None
    additional_info: str | None = None


# ── Section name enum ────────────────────────────────────────────────────────

VALID_SECTIONS: frozenset[str] = frozenset({
    "contact", "summary", "education", "experience", "skills",
    "publications", "certifications", "languages", "projects", "additional_info",
})


def is_valid_section(name: str) -> bool:
    return name in VALID_SECTIONS


# ── Completeness scoring ─────────────────────────────────────────────────────


def _str_of(obj: Any, key: str) -> str:
    if isinstance(obj, dict):
        v = obj.get(key, "")
        return v if isinstance(v, str) else ""
    return getattr(obj, key, "") or ""


def _list_of(obj: Any, key: str) -> list[Any]:
    if isinstance(obj, dict):
        v = obj.get(key, [])
        return v if isinstance(v, list) else []
    return getattr(obj, key, []) or []


def compute_completeness(data: MasterProfileData | dict[str, Any]) -> int:
    """Return 0-100 completeness score.

    +25  non-empty contact.full_name
    +25  at least one valid education entry
    +25  at least one valid experience entry
    +25  non-empty skills (any group)
    """
    score = 0

    contact = data.contact if isinstance(data, MasterProfileData) else data.get("contact", {})
    if _str_of(contact, "full_name").strip():
        score += 25

    edu_list = _list_of(data, "education")
    if edu_list and any(_str_of(e, "degree").strip() and _str_of(e, "institution").strip() for e in edu_list):
        score += 25

    exp_list = _list_of(data, "experience")
    if exp_list and any(_str_of(e, "role").strip() and _str_of(e, "company").strip() for e in exp_list):
        score += 25

    skills = data.skills if isinstance(data, MasterProfileData) else data.get("skills", {})
    if any(_list_of(skills, g) for g in ("technical", "domain", "tools", "soft")):
        score += 25

    return score


def profile_data_to_dict(data: MasterProfileData | dict[str, Any]) -> dict[str, Any]:
    """Normalize profile_data to a plain dict for JSON serialization."""
    if isinstance(data, MasterProfileData):
        return data.model_dump()
    return data


def empty_profile_data() -> dict[str, Any]:
    """Return a valid empty MasterProfileData dict for bootstrapping."""
    return MasterProfileData(
        contact=_empty_contact(),
        summary="",
        education=[],
        experience=[],
        skills=_empty_skills(),
        publications=[],
        certifications=[],
        languages=[],
        projects=[],
        additional_info="",
    ).model_dump()
