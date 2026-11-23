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


# ── Domain-track routing (generalized from NotebookLM extended_master_prompt) ──

DOMAIN_TRACK_GUIDANCE: dict[str, str] = {
    "academic_research": (
        "TARGET TRACK: Academic / Postdoc / Research.\n"
        "- Emphasize doctoral/graduate research, peer-reviewed publications, citation metrics, "
        "grant writing/compliance, student supervision/mentorship, and first-principles methodology.\n"
        "- Allow a thorough 2-3+ page CV with full publication citations and thesis details.\n"
        "- Tone: rigorous, methodology-driven, formal."
    ),
    "physical_engineering": (
        "TARGET TRACK: Physical / Process / Aerospace / Industrial Engineering.\n"
        "- Emphasize numerical/physical modeling (1D/3D, CFD, kinetics, thermodynamics, heat/mass transfer), "
        "laboratory/test-rig instrumentation, experimental validation, and process optimization.\n"
        "- Translate any software/quant/ML roles explicitly into physical modeling, sensor/DAQ pipelines, "
        "digital twins, or control loops under uncertainty.\n"
        "- Target a crisp 1-2 page ATS CV."
    ),
    "quant_software": (
        "TARGET TRACK: Quantitative Research / Systems / Software Engineering.\n"
        "- Emphasize production architecture, low-latency systems, numerical optimization, time-series/statistical "
        "modeling, automated execution/control loops, cloud/Linux infrastructure, and measurable impact.\n"
        "- Target a crisp 1-2 page ATS CV."
    ),
    "ai_ml": (
        "TARGET TRACK: AI / Machine Learning / Foundation Models.\n"
        "- Emphasize ML architectures, training/evaluation pipelines, alignment/safety/robustness, "
        "PyTorch/TensorFlow/LLM tooling, and production model deployment.\n"
        "- Target a crisp 1-2 page ATS CV."
    ),
    "general_industry": (
        "TARGET TRACK: General Industry.\n"
        "- Emphasize measurable business outcomes, ownership, domain alignment, and cross-functional impact.\n"
        "- Target a crisp 1-2 page ATS CV."
    ),
}


def detect_target_domain(job_description: str) -> str:
    """Infer the best domain routing track from the target job description."""
    text = job_description.lower()
    scores: dict[str, int] = {
        "academic_research": sum(
            1
            for kw in (
                "postdoc", "postdoctoral", "professor", "lecturer", "faculty",
                "research fellow", "grant", "peer-reviewed", "publications",
                "university", "department of", "principal investigator", "phd required",
            )
            if kw in text
        ),
        "physical_engineering": sum(
            1
            for kw in (
                "cfd", "ansys", "thermodynamics", "fluid dynamics", "heat transfer",
                "aerospace", "aftertreatment", "chemical engineering", "process engineer",
                "crystallization", "catalytic", "test-rig", "instrumentation", "finite element",
            )
            if kw in text
        ),
        "ai_ml": sum(
            1
            for kw in (
                "llm", "rlhf", "pytorch", "tensorflow", "machine learning",
                "deep learning", "foundation model", "ai safety", "mlops",
                "transformer", "nlp", "computer vision", "generative ai",
            )
            if kw in text
        ),
        "quant_software": sum(
            1
            for kw in (
                "quantitative", "quant ", "trading", "low-latency", "distributed systems",
                "backend", "software engineer", "kubernetes", "microservices", "rust",
                "c++", "fastapi", "postgresql", "devops",
            )
            if kw in text
        ),
    }
    best_domain, best_score = max(scores.items(), key=lambda item: item[1])
    return best_domain if best_score >= 2 else "general_industry"


def _build_evidence_section(evidence_chunks: list[dict[str, Any]] | None) -> str:
    if not evidence_chunks:
        return ""
    lines = [
        "--- VERIFIED EVIDENCE FROM CANDIDATE CORPUS ---",
        "The excerpts below were retrieved directly from the candidate's uploaded documents "
        "(papers, project reports, presentations, CVs). Use concrete metrics, project names, "
        "methodologies, and citations from these excerpts to ground the CV and Cover Letter. "
        "NEVER fabricate facts outside the Master Profile and Verified Evidence.\n",
    ]
    for idx, item in enumerate(evidence_chunks, start=1):
        source = item.get("source", "Document")
        excerpt = item.get("excerpt", "").strip()
        if excerpt:
            lines.append(f"[{idx}] Source: {source}\n{excerpt}\n")
    return "\n".join(lines)


MASTER_PROMPT_TEMPLATE: str = """\
Act as an expert executive recruiter, hiring manager, and ATS (Applicant Tracking
System) optimization specialist. Your task is to produce a tailored, ATS-compliant
single-column CV and a compelling single-page Cover Letter grounded strictly in
the candidate's Master Profile and Verified Evidence below.

--- CANDIDATE MASTER PROFILE ---
{profile_data}

{evidence_section}
--- TARGET JOB DESCRIPTION ---
{job_description}

--- ROLE CONTEXT & DOMAIN ROUTING ---
{role_context}
{domain_guidance}

{jev_context_section}

--- INSTRUCTIONS ---
1. Keyword Extraction & Grounded Matching:
   - Extract required hard skills, tools, domain keywords, and qualifications from the JD.
   - Integrate matching keywords naturally without stuffing. NEVER fabricate skills,
     degrees, metrics, or experiences not present in the Master Profile or Verified Evidence.
2. Cross-Domain Role Translation (MANDATORY):
   - For any experience entry from a different sector than the target role, populate
     its "relevance_note" field (1-2 concise sentences) translating transferable
     methodologies, systems, and outcomes into the target domain's language.
3. ATS-Compliant CV Rules:
   - Single-column structure, reverse-chronological order, standard section headers.
   - Open with a 3-4 line tailored "summary" synthesizing the candidate's strongest fit.
   - Start each experience bullet with a strong action verb and concrete outcome/metric
     drawn from the Master Profile or Verified Evidence.
4. Single-Page Cover Letter Rules (250-400 words):
   - Opening: strong, specific hook tied to the employer's mission/JD.
     DO NOT open with "I am writing to apply for..." or generic filler.
   - Body: 2-3 concrete technical/domain mappings citing specific projects, papers, or
     quantified achievements from the Master Profile / Verified Evidence.
   - Closing: confident, concise call to action and professional sign-off.{output_language}

--- OUTPUT FORMAT ---
You MUST output your response as a SINGLE JSON object with two top-level keys:
  - "cv": a CV object matching the CV schema below
  - "cover_letter": a cover letter object matching the Cover Letter schema below

The JSON MUST be valid and match the schemas exactly. Do not include any
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
    target_domain: str | None = None,
    evidence_chunks: list[dict[str, Any]] | None = None,
) -> str:
    """Fill the master prompt template with *profile*, *evidence_chunks*, and *job_description*.

    Returns the system prompt string to send to the LLM.
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

    resolved_domain = (
        target_domain
        if target_domain in DOMAIN_TRACK_GUIDANCE
        else detect_target_domain(job_description)
    )
    domain_guidance = DOMAIN_TRACK_GUIDANCE[resolved_domain]
    evidence_section = _build_evidence_section(evidence_chunks)

    cv_schema_text = json.dumps(CV_SCHEMA, indent=2)
    cover_schema_text = json.dumps(COVER_LETTER_SCHEMA, indent=2)

    # Build Jev context section if provided
    jev_section = _build_jev_prompt_section(jev_context) if jev_context else ""

    return MASTER_PROMPT_TEMPLATE.format(
        profile_data=profile_text,
        evidence_section=evidence_section,
        job_description=job_description,
        role_context=role_context,
        domain_guidance=domain_guidance,
        jev_context_section=jev_section,
        cv_schema=cv_schema_text,
        cover_letter_schema=cover_schema_text,
        output_language=(
            f"\n5. Output Language: Write ALL content in {LANGUAGE_LABELS.get(output_language, output_language)} "
            f"({output_language}). Keep proper nouns and technical tool names intact."
            if output_language != "en"
            else ""
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
        parts.append(
            f"Seniority level: {jev_context['seniority_level']} ({jev_context.get('seniority_label', '')})"
        )
    if jev_context.get("salary_bracket"):
        parts.append(f"Salary bracket: {jev_context['salary_bracket']}")
    if jev_context.get("has_red_flags"):
        parts.append(
            f"Has red flags: {'yes' if jev_context['has_red_flags'] > 0.5 else 'no'} ({jev_context['has_red_flags']:.2f} confidence)"
        )
    if jev_context.get("remote_ok"):
        parts.append(
            f"Remote work: {'yes' if jev_context['remote_ok'] > 0.5 else 'no'} ({jev_context['remote_ok']:.2f} confidence)"
        )
    parts.append(
        "\nUse this structured analysis as CONTEXT to guide your CV generation. "
        "The candidate's profile and the job description are the authoritative "
        "sources; Jev's classification helps prioritize which skills to feature."
    )
    return "\n".join(parts)
