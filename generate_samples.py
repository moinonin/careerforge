"""Generate sample CVs directly from parsed profile data (no LLM).

Flow:
1. Parse reference CV with pymupdf + Jev → MasterProfileData
2. Enrich with role-specific additions
3. Render to DOCX + PDF using DocxRenderer/PDFRenderer

Usage:
    .venv/bin/python generate_samples.py [--count N]
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.llm.docx_renderer import DocxRenderer
from backend.llm.pdf_renderer import PDFRenderer
from backend.profiles.jev_parser import parse_cv_with_jev

ARTIFACTS = Path(__file__).resolve().parent / "artifacts"


async def generate_cv(
    job_title: str,
    company_name: str,
    job_description: str,
    output_prefix: str,
) -> dict | None:
    ref_cv_path = ARTIFACTS / "nicolus-rotich-oxford-cv.pdf"
    with open(ref_cv_path, "rb") as f:
        ref_bytes = f.read()

    profile = await parse_cv_with_jev(ref_bytes, "nicolus-rotich-oxford-cv.pdf")
    cv_dict = _profile_to_dict(profile, job_title, company_name, job_description)

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
            "bullets": _bullets(job_title),
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


def _bullets(job_title):
    return {
        "ML Engineer": ["Designed ML pipelines processing 10M+ predictions daily", "Reduced inference latency by 40% through optimization", "Implemented A/B testing improving accuracy by 15%"],
        "Quantitative Researcher": ["Developed strategies generating 2.3x Sharpe ratio over 12-month backtest", "Built predictive models on 500GB+ datasets reducing latency by 60%", "Deployed 12+ strategies across 5 asset classes"],
        "Senior Backend Engineer": ["Architected microservices handling 50K+ RPS with <10ms p99 latency", "Reduced infrastructure costs by 35% through auto-scaling", "Led migration to Kubernetes across 8 services"],
    }.get(job_title, ["Demonstrated expertise with measurable impact on business metrics", "Collaborated cross-functionally to deliver high-quality solutions"])


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
        print(f"  {r['pdf'].name}")
        print(f"  {r['docx'].name}")


if __name__ == "__main__":
    asyncio.run(main())