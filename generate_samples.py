"""Generate sample CVs using pymupdf + Jev for parsing and Nous LLM for enrichment.

Flow:
1. Parse reference CV with pymupdf + Jev → MasterProfileData
2. Enrich with role-specific additions via Nous LLM (ling-3.0-flash-fin:free)
3. Render to DOCX + PDF using DocxRenderer/PDFRenderer

Usage:
    .venv/bin/python generate_samples.py [--count N]
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from openai import AsyncOpenAI
from backend.llm.docx_renderer import DocxRenderer
from backend.llm.pdf_renderer import PDFRenderer
from backend.profiles.jev_parser import parse_cv_with_jev

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"
NOUS_BASE_URL = os.environ.get("NOUS_BASE_URL", "http://localhost:8645/v1")
NOUS_MODEL = os.environ.get("NOUS_MODEL", "inclusionai/ling-3.0-flash-fin:free")

ROLE_BULLETS = {
    "ML Engineer": [
        "Designed ML pipelines processing 10M+ predictions daily",
        "Reduced inference latency by 40% through optimization",
        "Implemented A/B testing improving accuracy by 15%",
    ],
    "Quantitative Researcher": [
        "Developed strategies generating 2.3x Sharpe ratio over 12-month backtest",
        "Built predictive models on 500GB+ datasets reducing latency by 60%",
        "Deployed 12+ strategies across 5 asset classes",
    ],
    "Senior Backend Engineer": [
        "Architected microservices handling 50K+ RPS with <10ms p99 latency",
        "Reduced infrastructure costs by 35% through auto-scaling",
        "Led migration to Kubernetes across 8 services",
    ],
}


async def generate_cv(job_title, company_name, job_description, output_prefix):
    ref_cv_path = ARTIFACTS / "nicolus-rotich-oxford-cv.pdf"
    with open(ref_cv_path, "rb") as f:
        ref_bytes = f.read()

    profile = await parse_cv_with_jev(ref_bytes, "nicolus-rotich-oxford-cv.pdf")
    cv_dict = _profile_to_dict(profile, job_title, company_name, job_description)

    # Enrich with Nous LLM
    try:
        cv_dict = await _enrich_with_llm(cv_dict, job_description, job_title)
    except Exception as exc:
        print(f"  ⚠ LLM enrichment failed: {exc}, using base CV")

    docx_path = ARTIFACTS / f"{output_prefix}.docx"
    renderer = DocxRenderer()
    doc = renderer.render(cv_dict)
    doc.save(str(docx_path))

    pdf_path = ARTIFACTS / f"{output_prefix}.pdf"
    pdf_renderer = PDFRenderer()
    await pdf_renderer.render(data=cv_dict, output_path=str(pdf_path))

    json_path = ARTIFACTS / f"{output_prefix}.json"
    with open(json_path, "w") as f:
        json.dump(cv_dict, f, indent=2, default=str)

    return {"prefix": output_prefix, "pdf": str(pdf_path), "docx": str(docx_path)}


async def _enrich_with_llm(cv_dict, job_description, job_title):
    client = AsyncOpenAI(base_url=NOUS_BASE_URL, api_key="test", timeout=120.0)

    prompt = (
        "You are a CV enhancement assistant. Given the following CV data and job description, "
        "improve the CV content for this specific role.\n\n"
        f"JOB DESCRIPTION: {job_description}\n\n"
        f"CURRENT CV DATA: {json.dumps(cv_dict, indent=2)}\n\n"
        "TASK: Return ONLY valid JSON with these exact fields, no markdown:\n"
        '{"summary": "A compelling 3-4 sentence professional summary tailored to the role", '
        '"experience": [{"role": "...", "company": "...", '
        '"bullets": ["3 quantified achievement bullets tailored to the role"]}], '
        '"skills": {"technical": ["3 relevant technical skills"], "domain": ["2 domain skills"], '
        '"tools": ["3 tools/frameworks"], "soft": ["2 soft skills"]}, '
        '"cover_letter_summary": "1-2 sentence cover letter hook"}\n\n'
        "Rules:\n"
        f"- Use the candidate's actual background (chemical engineering, ML, quant research)\n"
        f"- Reframe experience to highlight transferable skills for {job_title}\n"
        "- All bullets must be quantified or specific\n"
        "- Return valid JSON only, no markdown, no explanation"
    )

    response = await client.chat.completions.create(
        model=NOUS_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
        temperature=0.1,
        reasoning_effort="none",
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("Empty LLM response")
    parsed = json.loads(content)

    # Merge LLM output into cv_dict
    if "summary" in parsed:
        cv_dict["summary"] = parsed["summary"]
    if "experience" in parsed and parsed["experience"]:
        cv_dict["experience"] = parsed["experience"]
    if "skills" in parsed:
        cv_dict["skills"] = parsed["skills"]

    return cv_dict


def _profile_to_dict(profile, job_title, company_name, job_description):
    contact = profile.contact.model_dump() if hasattr(profile.contact, "model_dump") else profile.contact
    skills = profile.skills.model_dump() if hasattr(profile.skills, "model_dump") else profile.skills

    experience = []
    for exp in profile.experience:
        experience.append({
            "role": exp.role or job_title,
            "company": exp.company or company_name,
            "location": exp.location or "",
            "start_date": exp.start_date or "",
            "end_date": exp.end_date or "",
            "bullets": ROLE_BULLETS.get(job_title, [
                "Demonstrated expertise with measurable impact on business metrics",
                "Collaborated cross-functionally to deliver high-quality solutions",
            ]),
        })

    education = []
    for edu in profile.education:
        education.append({
            "degree": edu.degree or "",
            "institution": edu.institution or "",
            "location": edu.location or "",
            "start_date": edu.start_date or "",
            "end_date": edu.end_date or "",
            "thesis": edu.thesis or "",
        })

    publications = [{"citation": p.citation or "", "year": p.year, "doi": p.doi, "link": p.link} for p in profile.publications]
    languages = [{"language": l.language or "", "proficiency": l.proficiency or ""} for l in profile.languages]
    certifications = [{"name": c.name or "", "issuer": c.issuer or "", "year": c.year} for c in profile.certifications]
    projects = [{"name": p.name or "", "description": p.description or "", "tech_stack": p.tech_stack or [], "link": p.link} for p in profile.projects]

    summary = profile.summary or ""
    if job_title:
        summary += f"\n\n{job_title} at {company_name}"

    return {
        "full_name": contact.get("full_name", "Sample User"),
        "location": contact.get("location", "Remote"),
        "phone": contact.get("phone", ""),
        "email": contact.get("email", "sample@example.com"),
        "linkedin": contact.get("linkedin", ""),
        "website_portfolio": contact.get("website_portfolio", ""),
        "role": job_title,
        "company": company_name,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "publications": publications,
        "languages": languages,
        "certifications": certifications,
        "projects": projects,
        "additional_info": profile.additional_info or "",
    }


async def main():
    ARTIFACTS.mkdir(exist_ok=True)
    jobs = [
        ("ML Engineer", "DeepMind", "Build and deploy ML models at scale.", "sample_ml_cv"),
        ("Quantitative Researcher", "G-Research", "Develop algorithmic trading strategies.", "sample_quant_cv"),
        ("Senior Backend Engineer", "Spotify", "Design scalable distributed systems.", "sample_backend_cv"),
    ]

    count = len(jobs)
    if "--count" in sys.argv:
        idx = sys.argv.index("--count") + 1
        if idx < len(sys.argv):
            count = min(int(sys.argv[idx]), len(jobs))

    print(f"Generating {count} sample CVs...\n")
    results = []
    for jt, cn, jd, prefix in jobs[:count]:
        print(f"→ {jt} @ {cn}...")
        try:
            result = await generate_cv(jt, cn, jd, prefix)
            if result:
                results.append(result)
                print(f"  ✓ {Path(result['pdf']).name}")
            else:
                print(f"  ✗ Failed")
        except Exception as exc:
            print(f"  ✗ Error: {exc}")

    print(f"\nDone: {len(results)}/{count} CVs in {ARTIFACTS}/")
    for r in results:
        print(f"  {Path(r['pdf']).name}")
        print(f"  {Path(r['docx']).name}")


if __name__ == "__main__":
    asyncio.run(main())
