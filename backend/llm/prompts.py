"""Prompt Assembly Service.

Fills the generic master prompt template (from SPRINTS.md Part A.2) with a
user's master profile data and a job description, producing the system prompt
sent to the LLM.

The CV output schema (CV_SCHEMA) and Cover Letter schema (COVER_LETTER_SCHEMA)
are the JSON Schema dicts the LLM must produce — see the master prompt template
in SPRINTS.md Part A.2 for the authoritative definition.
"""

from __future__ import annotations

import json
from typing import Any

from backend.profiles.schemas import (
    CertificationEntry,
    ContactInfo,
    EducationEntry,
    ExperienceEntry,
    LanguageEntry,
    MasterProfileData,
    ProjectEntry,
    PublicationEntry,
    SkillsGroup,
)

# ── Output schemas (authoritative definitions match SPRINTS.md Part A.2) ─────

CV_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "contact": {
            "type": "object",
            "properties": {
                "full_name": {"type": "string"},
                "location": {"type": "string"},
                "phone": {"type": "string"},
                "email": {"type": "string"},
                "linkedin": {"type": "string"},
                "website_portfolio": {"type": "string"},
            },
            "required": ["full_name", "location"],
        },
        "skills": {
            "type": "object",
            "properties": {
                "technical": {"type": "array", "items": {"type": "string"}},
                "domain": {"type": "array", "items": {"type": "string"}},
                "tools": {"type": "array", "items": {"type": "string"}},
                "soft": {"type": "array", "items": {"type": "string"}},
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "role": {"type": "string"},
                    "company": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "relevance_note": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["role", "company"],
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "degree": {"type": "string"},
                    "institution": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "thesis": {"type": "string"},
                    "details": {"type": "string"},
                },
                "required": ["degree", "institution"],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "tech_stack": {"type": "array", "items": {"type": "string"}},
                    "link": {"type": "string"},
                },
                "required": ["name", "description"],
            },
        },
        "publications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "citation": {"type": "string"},
                    "year": {"type": "string"},
                    "doi": {"type": "string"},
                    "link": {"type": "string"},
                },
                "required": ["citation"],
            },
        },
        "certifications": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "issuer": {"type": "string"},
                    "year": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        "languages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "language": {"type": "string"},
                    "proficiency": {"type": "string"},
                },
                "required": ["language", "proficiency"],
            },
        },
        "additional_info": {"type": "string"},
    },
    "required": ["summary", "contact", "skills", "experience"],
}


COVER_LETTER_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "header": {"type": "string"},
        "salutation": {"type": "string"},
        "opening": {"type": "string"},
        "body_paragraphs": {"type": "array", "items": {"type": "string"}},
        "call_to_action": {"type": "string"},
        "closing": {"type": "string"},
        "signature": {"type": "string"},
    },
    "required": ["header", "salutation", "opening", "body_paragraphs", "closing", "signature"],
}


# ── Current-role tracking (optional context for prompt assembly) ───────────────

# The master profile itself doesn't store "current role" as a separate field —
# we infer it from the most recent experience entry whose end_date is empty
# or "Present".  The generator may pass this in via role_context if desired.


def _infer_current_role(profile: MasterProfileData) -> str:
    """Return a short 'Currently: Role at Company' string, or empty."""
    for exp in reversed(profile.experience):
        if exp.end_date.strip().lower() in ("", "present", "now"):
            role = exp.role.strip()
            company = exp.company.strip()
            if role and company:
                return f"Currently working as {role} at {company}."
            if role:
                return f"Currently: {role}."
    return ""


# ── Formatters ────────────────────────────────────────────────────────────────


def _fmt_contact(c: ContactInfo) -> str:
    lines: list[str] = []
    if c.full_name:
        lines.append(f"  Full Name: {c.full_name}")
    if c.location:
        lines.append(f"  Location: {c.location}")
    if c.phone:
        lines.append(f"  Phone: {c.phone}")
    if c.email:
        lines.append(f"  Email: {c.email}")
    if c.linkedin:
        lines.append(f"  LinkedIn: {c.linkedin}")
    if c.website_portfolio:
        lines.append(f"  Website/Portfolio: {c.website_portfolio}")
    return "\n".join(lines)


def _fmt_skills(s: SkillsGroup) -> str:
    parts: list[str] = []
    if s.technical:
        parts.append(f"  Technical: {', '.join(s.technical)}")
    if s.domain:
        parts.append(f"  Domain: {', '.join(s.domain)}")
    if s.tools:
        parts.append(f"  Tools: {', '.join(s.tools)}")
    if s.soft:
        parts.append(f"  Soft: {', '.join(s.soft)}")
    return "\n".join(parts)


def _fmt_experience(exp_list: list[ExperienceEntry]) -> str:
    """Format experience newest-first (reverse chronological)."""
    lines: list[str] = []
    for exp in reversed(exp_list):
        line = f"  {exp.role} at {exp.company}"
        if exp.location:
            line += f", {exp.location}"
        if exp.start_date:
            line += f" ({exp.start_date}"
            end = exp.end_date.strip()
            if end and end.lower() not in ("", "present", "now"):
                line += f" – {end}"
            else:
                line += " – Present"
            line += ")"
        lines.append(line)
        for b in exp.bullets:
            lines.append(f"    - {b}")
    return "\n".join(lines)


def _fmt_education(edu_list: list[EducationEntry]) -> str:
    lines: list[str] = []
    for edu in edu_list:
        line = f"  {edu.degree}"
        if edu.institution:
            line += f" at {edu.institution}"
        if edu.location:
            line += f", {edu.location}"
        if edu.start_date:
            line += f" ({edu.start_date}"
            end = edu.end_date.strip()
            if end:
                line += f" – {end}"
            else:
                line += " – Present"
            line += ")"
        lines.append(line)
        if edu.thesis:
            lines.append(f"    Thesis: {edu.thesis}")
        for d in edu.details:
            if d:
                lines.append(f"    {d}")
    return "\n".join(lines)


def _fmt_projects(proj_list: list[ProjectEntry]) -> str:
    lines: list[str] = []
    for p in proj_list:
        line = f"  {p.name}"
        lines.append(line)
        if p.description:
            lines.append(f"    {p.description}")
        if p.tech_stack:
            lines.append(f"    Tech: {', '.join(p.tech_stack)}")
        if p.link:
            lines.append(f"    Link: {p.link}")
    return "\n".join(lines)


def _fmt_publications(pub_list: list[PublicationEntry]) -> str:
    lines: list[str] = []
    for pub in pub_list:
        line = f"  {pub.citation}"
        if pub.year:
            line += f" ({pub.year})"
        if pub.doi:
            line += f" — DOI: {pub.doi}"
        lines.append(line)
        if pub.link:
            lines.append(f"    Link: {pub.link}")
    return "\n".join(lines)


def _fmt_certifications(cert_list: list[CertificationEntry]) -> str:
    lines: list[str] = []
    for cert in cert_list:
        line = f"  {cert.name}"
        if cert.issuer:
            line += f" — {cert.issuer}"
        if cert.year:
            line += f" ({cert.year})"
        lines.append(line)
    return "\n".join(lines)


def _fmt_languages(lang_list: list[LanguageEntry]) -> str:
    return "\n".join(f"  {lang.language}: {lang.proficiency}" for lang in lang_list)


# ── Master prompt template ────────────────────────────────────────────────────
#
# This is the generic template from SPRINTS.md Part A.2.  The placeholders
# ``{profile_data}``, ``{job_description}``, ``{output_schema}`` and
# ``{role_context}`` are filled by ``assemble_prompt`` below.


MASTER_PROMPT_TEMPLATE: str = """\
You are a professional CV and cover letter writer with expertise in crafting
ATS-optimized, achievement-focused career documents.  Your task is to produce
a CV and a cover letter for the candidate described below, tailored to the
target job description.

--- CANDIDATE MASTER PROFILE ---
{profile_data}

--- TARGET JOB DESCRIPTION ---
{job_description}

--- ROLE CONTEXT (for tailoring) ---
{role_context}

{jev_context_section}

--- INSTRUCTIONS ---
1. Study the candidate's master profile above carefully.
2. Study the job description and role context.
3. Produce a CV that is:
   - Tailored to the job description: highlight the most relevant experience,
     skills, and achievements for THIS role.
   - Achievement-focused: use metrics, outcomes, and impact where possible.
     Expand on brief entries from the master profile by turning them into
     accomplishment statements (e.g., "Improved X by Y%, saving $Z").
   - ATS-optimized: use standard section headings and keyword-rich language
     that mirrors the job description.
   - Honest: do NOT invent facts not supported by the master profile, but you
     MAY rephrase, expand, and contextualize existing information into strong
     achievement statements.
4. Produce a cover letter that:
   - Opens with a strong, specific hook connecting the candidate to the role.
   - Body paragraphs connect 2-3 specific achievements to the employer's needs.
   - Closes with a confident call to action.
   - Is written in a professional, warm tone appropriate for the industry.

--- OUTPUT FORMAT ---
You MUST output your response as a SINGLE JSON object with two top-level keys:
  - "cv": a CV object matching the CV schema below
  - "cover_letter": a cover letter object matching the Cover Letter schema below

The JSON MUST be valid and match the schemas exactly.  Do not include any
markdown formatting, explanations, or text outside the JSON object.

CV Schema (output "cv" must conform to this):
{cv_schema}

Cover Letter Schema (output "cover_letter" must conform to this):
{cover_letter_schema}

Output ONLY the JSON object — no fences, no preamble, no commentary.
"""


LANGUAGE_LABELS: dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "de": "German",
    "fr": "French",
    "fi": "Finnish",
}


def assemble_prompt(
    profile: MasterProfileData,
    job_description: str,
    *,
    role_context: str = "",
    output_language: str = "en",
    jev_context: dict[str, Any] | None = None,
) -> str:
    """Fill the master prompt template with *profile* and *job_description*.

    Returns the system prompt string to send to the LLM.

    If *role_context* is empty, a ``"Currently: ...`` line is auto-derived
    from the most recent experience entry whose end_date is blank or "Present".

    If *jev_context* is provided, Jev's structured job analysis is inserted
    into the prompt to guide the LLM's CV generation.
    """
    parts: list[str] = []

    c = profile.contact
    contact_lines = _fmt_contact(c)
    if contact_lines:
        parts.append("CONTACT INFORMATION:\n" + contact_lines)

    if profile.summary:
        parts.append(f"\nPROFESSIONAL SUMMARY:\n{profile.summary}")

    s = profile.skills
    skills_text = _fmt_skills(s)
    if skills_text:
        parts.append("\nSKILLS:\n" + skills_text)

    exp_text = _fmt_experience(profile.experience)
    if exp_text:
        parts.append("\nPROFESSIONAL EXPERIENCE:\n" + exp_text)

    edu_text = _fmt_education(profile.education)
    if edu_text:
        parts.append("\nEDUCATION:\n" + edu_text)

    proj_text = _fmt_projects(profile.projects)
    if proj_text:
        parts.append("\nPROJECTS:\n" + proj_text)

    pub_text = _fmt_publications(profile.publications)
    if pub_text:
        parts.append("\nPUBLICATIONS:\n" + pub_text)

    cert_text = _fmt_certifications(profile.certifications)
    if cert_text:
        parts.append("\nCERTIFICATIONS:\n" + cert_text)

    lang_text = _fmt_languages(profile.languages)
    if lang_text:
        parts.append("\nLANGUAGES:\n" + lang_text)

    if profile.additional_info:
        parts.append(f"\nADDITIONAL INFORMATION:\n{profile.additional_info}")

    profile_text = "\n".join(parts)

    # Auto-derive current role context if none provided
    if not role_context:
        role_context = _infer_current_role(profile) or "No additional role context provided."

    cv_schema_text = json.dumps(CV_SCHEMA, indent=2)
    cover_schema_text = json.dumps(COVER_LETTER_SCHEMA, indent=2)

    # Build Jev context section if provided
    jev_section = _build_jev_prompt_section(jev_context) if jev_context else ""

    return MASTER_PROMPT_TEMPLATE.format(
        profile_data=profile_text,
        job_description=job_description,
        role_context=role_context,
        jev_context_section=jev_section,
        cv_schema=cv_schema_text,
        cover_letter_schema=cover_schema_text,
        output_language=(
            f"\n\nOUTPUT LANGUAGE: Respond in {LANGUAGE_LABELS.get(output_language, output_language)}. "
            f"Use {output_language} language for all content."
            if output_language != "en" else ""
        ),
    )


def _build_jev_prompt_section(jev_context: dict[str, Any]) -> str:
    """Build a Jev classification section for the prompt."""
    parts = ["--- JEV JOB ANALYSIS (structured classification) ---\n"]
    if jev_context.get("primary_skill_category"):
        parts.append(f"Primary skill category: {jev_context['primary_skill_category']}")
    if jev_context.get("primary_tech_stack"):
        parts.append(f"Primary tech stack: {jev_context['primary_tech_stack']}")
    if jev_context.get("seniority_level"):
        parts.append(f"Seniority level: {jev_context['seniority_level']} ({jev_context.get('seniority_label', '')})")
    if jev_context.get("salary_bracket"):
        parts.append(f"Salary bracket: {jev_context['salary_bracket']}")
    if jev_context.get("has_red_flags"):
        parts.append(f"Has red flags: {'yes' if jev_context['has_red_flags'] > 0.5 else 'no'} ({jev_context['has_red_flags']:.2f} confidence)")
    if jev_context.get("remote_ok"):
        parts.append(f"Remote work: {'yes' if jev_context['remote_ok'] > 0.5 else 'no'} ({jev_context['remote_ok']:.2f} confidence)")
    parts.append(
        "\nUse this structured analysis as CONTEXT to guide your CV generation. "
        "The candidate's profile and the job description are the authoritative "
        "sources; Jev's classification helps prioritize which skills to feature."
    )
    return "\n".join(parts)
