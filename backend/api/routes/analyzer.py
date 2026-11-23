"""Job Post Analyzer API — public, no-account-required endpoint.

Anyone can paste a job description and receive an immediate breakdown:
required skills, implied skills, red flags, salary estimate, and company
research summary. This is the freemium entry point (spec Section 1.6).

Endpoint: POST /api/v1/analyzer
No authentication required.
"""

from __future__ import annotations

import re
from typing import Any

from backend.database import get_session
from backend.llm.adapter import GenerationError
from backend.llm.router import build_adapter
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["analyzer"])


class AnalyzerRequest(BaseModel):
    """Request body for ``POST /api/v1/analyzer``."""

    job_description: str
    company_name: str | None = None


class AnalyzerResponse(BaseModel):
    """Response body for ``POST /api/v1/analyzer``."""

    required_skills: list[str]
    implied_skills: list[str]
    red_flags: list[str]
    salary_estimate: dict[str, Any] | None
    company_research: dict[str, Any] | str | None
    keyword_coverage: dict[str, Any] | None = None


@router.post("", response_model=AnalyzerResponse, status_code=status.HTTP_200_OK)
async def analyze_job_post(
    request: AnalyzerRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> dict[str, Any]:
    """Analyze a job description and return a breakdown.

    Body::
        {"job_description": "Senior Python Engineer at ..."}

    Returns::
        {
            "required_skills": ["Python", "FastAPI", ...],
            "implied_skills": ["Docker", "CI/CD", ...],
            "red_flags": ["vague requirements", ...],
            "salary_estimate": {"range": "$100K-$140K", ...},
            "company_research": "...",
            "keyword_coverage": null
        }

    No account required.  The analysis is performed by the platform's
    default LLM provider.
    """
    job_description = request.job_description.strip()
    company_name = request.company_name or None

    if not job_description or len(job_description) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="job_description must be at least 10 characters",
        )

    try:
        result = await _run_analyzer(job_description, company_name)
    except GenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM analysis failed: {exc}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Analyzer failed: {exc}",
        ) from exc

    return result


def _normalize_skill_list(data: Any) -> list[str]:
    """Normalize LLM response skill data to a list of strings.

    The LLM sometimes returns skills as ``{"Skill Name": True}`` dicts
    instead of plain string lists. This converts both formats to a clean
    list of skill name strings.
    """
    if isinstance(data, list):
        return [str(s) for s in data if isinstance(s, str)]
    if isinstance(data, dict):
        return [str(k) for k in data.keys() if k]
    return []


_SALARY_BRACKET_LABELS: dict[str, str] = {
    "under_80k": "$60,000 - $80,000",
    "80k_120k": "$80,000 - $120,000",
    "120k_160k": "$120,000 - $160,000",
    "160k_200k": "$160,000 - $200,000",
    "200k_plus": "$200,000+",
}

_KNOWN_SKILLS: tuple[str, ...] = (
    "Python", "FastAPI", "Django", "Flask", "C++", "Rust", "Java", "Kotlin", "Go",
    "TypeScript", "JavaScript", "React", "Next.js", "Node.js", "SQL", "PostgreSQL",
    "Redis", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Terraform", "Linux",
    "PyTorch", "TensorFlow", "Scikit-Learn", "Spark", "Kafka", "GraphQL", "gRPC",
    "ANSYS", "MATLAB", "CFD", "Git", "CI/CD", "Machine Learning", "Statistical Modeling",
    "Market Microstructure", "Systematic Trading",
)


_RED_FLAG_RULES: tuple[tuple[str, str], ...] = (
    (
        r"\b(unpaid\s+overtime|unpaid\s+weekend|70[\s-]?hour|60[\s-]?hour|mandatory\s+overtime|nights?\s+and\s+weekends?)\b",
        "Excessive hours or unpaid overtime expectations mentioned.",
    ),
    (
        r"\b(rockstar|ninja|guru|10x\s+engineer|wear\s+(?:many|every)\s+hats?)\b",
        "Buzzword-heavy framing ('rockstar/ninja/wear every hat') — clarify actual role boundaries.",
    ),
    (
        r"\b(equity[\s-]?only|unpaid\s+trial|salary\s+tbd|compensation\s+tbd)\b",
        "Unclear or deferred cash compensation (equity-only / TBD).",
    ),
    (
        r"\b(fast[\s-]?paced\s+family|like\s+a\s+family|work\s+hard\s+play\s+hard)\b",
        "Culture phrasing ('like a family' / 'work hard play hard') can signal weak work-life boundaries.",
    ),
    (
        r"\b(no\s+clear\s+(?:job\s+)?scope|duties\s+as\s+assigned\s+with\s+no\s+limits)\b",
        "Vague or unbounded role scope.",
    ),
)


async def _fetch_company_research(
    company_name: str | None,
    job_description: str,
    *,
    domain: str | None = None,
    tech_stack: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch brief verified company context (Wikipedia REST API) + JD clues."""
    stack_str = ", ".join(tech_stack[:6]) if tech_stack else None
    if company_name and company_name.strip():
        clean_name = company_name.strip()
        try:
            import urllib.parse

            import httpx

            slug = urllib.parse.quote(clean_name.replace(" ", "_"))
            url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{slug}"
            async with httpx.AsyncClient(timeout=3.0, follow_redirects=True) as http:
                resp = await http.get(url, headers={"User-Agent": "CareerForgeAI/1.0"})
                if resp.status_code == 200:
                    data = resp.json()
                    extract = str(data.get("extract") or "").strip()
                    if extract and data.get("type") != "disambiguation":
                        return {
                            "company": data.get("title") or clean_name,
                            "summary": extract[:500],
                            "domain": data.get("description") or domain,
                            "technology_stack": stack_str,
                            "source": data.get("content_urls", {}).get("desktop", {}).get("page"),
                        }
        except Exception:
            pass

        return {
            "company": clean_name,
            "summary": (
                f"No public encyclopedia entry found for {clean_name}. "
                "Verify company stage, funding, team size, and engineering culture during interviews."
            ),
            "domain": domain,
            "technology_stack": stack_str,
            "source": None,
        }

    return {
        "company": None,
        "summary": (
            "Enter a company name above to look up public background, "
            "or verify company stage, team structure, and compensation bands before applying."
        ),
        "domain": domain,
        "technology_stack": stack_str,
        "source": None,
    }


async def _fallback_s1_analyzer(
    job_description: str,
    company_name: str | None,
) -> dict[str, Any]:
    """Local CareerForge-S1 fallback when the external LLM endpoint is unavailable."""
    from backend.s1 import get_decision_client

    async with get_decision_client() as client:
        s1 = await client.analyze_job(job_description, company_name)

    lower = job_description.lower()
    found_skills = [s for s in _KNOWN_SKILLS if re.search(rf"\b{re.escape(s.lower())}\b", lower)]
    if not found_skills and s1.tech_stack:
        found_skills = [s1.tech_stack.choice.replace("_", " ").title()]

    implied: list[str] = []
    if s1.skill_category:
        implied.append(f"{s1.skill_category.choice.title()} Engineering")
    if s1.seniority_level:
        sen_idx = str(int(round(s1.seniority_level.score)))
        sen_label = s1.seniority_level.legend.get(sen_idx, "Mid-Senior")
        implied.append(f"{sen_label.title()}-level ownership")
    if s1.remote_ok and s1.remote_ok.value >= 0.5:
        implied.append("Async / distributed collaboration")

    red_flags: list[str] = [
        msg for pattern, msg in _RED_FLAG_RULES if re.search(pattern, lower)
    ]
    if not red_flags and s1.has_red_flags and s1.has_red_flags.value >= 0.65:
        red_flags.append(
            f"Potential job posting red flags detected ({s1.has_red_flags.value:.0%} confidence) — "
            "review role scope, working hours, and compensation transparency."
        )

    bracket = s1.salary_bracket.choice if s1.salary_bracket else "120k_160k"
    salary_estimate = {
        "range": _SALARY_BRACKET_LABELS.get(bracket, "$100,000 - $150,000"),
        "currency": "USD",
        "location": "Remote" if (s1.remote_ok and s1.remote_ok.value >= 0.5) else "Onsite / Hybrid",
    }
    domain_label = (
        f"{s1.skill_category.choice.title()} Engineering" if s1.skill_category else None
    )
    company_summary = await _fetch_company_research(
        company_name,
        job_description,
        domain=domain_label,
        tech_stack=found_skills,
    )
    return {
        "required_skills": found_skills,
        "implied_skills": implied,
        "red_flags": red_flags,
        "salary_estimate": salary_estimate,
        "company_research": company_summary,
        "keyword_coverage": None,
    }


async def _run_analyzer(
    job_description: str,
    company_name: str | None,
) -> dict[str, Any]:
    """Build the analyzer prompt and call the LLM, falling back to CareerForge-S1 on error."""
    prompt = _build_analyzer_prompt(job_description, company_name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "required_skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "implied_skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "red_flags": {
                "type": "array",
                "items": {"type": "string"},
            },
            "salary_estimate": {
                "type": "object",
                "properties": {
                    "range": {"type": "string"},
                    "currency": {"type": "string"},
                    "location": {"type": "string"},
                },
            },
            "company_research": {"type": "string"},
        },
        "required": ["required_skills", "implied_skills", "red_flags"],
    }

    try:
        adapter = build_adapter()
        response = await adapter.generate(prompt, schema)
    except Exception:
        return await _fallback_s1_analyzer(job_description, company_name)

    result: dict[str, Any] = {
        "required_skills": _normalize_skill_list(response.get("required_skills", [])),
        "implied_skills": _normalize_skill_list(response.get("implied_skills", [])),
        "red_flags": _normalize_skill_list(response.get("red_flags", [])),
        "salary_estimate": response.get("salary_estimate"),
        "company_research": response.get("company_research"),
        "keyword_coverage": None,
    }

    return result


def _build_analyzer_prompt(
    job_description: str,
    company_name: str | None,
) -> str:
    """Build the analyzer system prompt."""
    company_section = (
        f"Company name: {company_name}\n" if company_name else "No company name provided.\n"
    )
    return (
        "ACT AS AN EXPERT TECHNICAL RECRUITER AND JOB MARKET ANALYST.\n\n"
        "You are analyzing a job posting. Provide a detailed breakdown of the job.\n\n"
        f"Company:\n{company_section}\n"
        "Job Description:\n"
        f"{job_description}\n\n"
        "Analyze this job posting and return a JSON object with exactly these fields:\n\n"
        "1. **required_skills**: All hard skills, tools, platforms, languages, and "
        "frameworks explicitly required in the job description.\n\n"
        "2. **implied_skills**: Skills NOT explicitly stated but strongly implied by the "
        "role context (e.g., 'Docker' for 'production pipelines', 'CI/CD' for 'shipping code').\n\n"
        "3. **red_flags**: Vague requirements, unrealistic skill combinations, signs the "
        "job description was poorly written, or potential warning signs for candidates.\n\n"
        "4. **salary_estimate**: An estimated salary range based on the role, required skills, "
        "and market data. Include 'range' (e.g., '$100K-$140K'), 'currency', and 'location'.\n\n"
        "5. **company_research**: A brief summary of the company's likely domain, size indicators, "
        "and technology stack based on the job description and company name.\n\n"
        "Return ONLY a valid JSON object. No markdown, no commentary, no preamble."
    )


# ── Stop-words for ATS keyword extraction ──────────────────────────────

_ANALYZE_STOP_WORDS: frozenset[str] = frozenset(
    {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "need",
        "dare",
        "ought",
        "used",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "as",
        "not",
        "no",
        "nor",
        "so",
        "if",
        "then",
        "than",
        "too",
        "very",
        "just",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "also",
        "any",
        "because",
        "before",
        "between",
        "both",
        "each",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "into",
        "over",
        "under",
        "up",
        "out",
        "off",
        "down",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "i",
        "me",
        "my",
        "we",
        "our",
        "you",
        "your",
        "he",
        "him",
        "his",
        "she",
        "her",
        "they",
        "them",
        "their",
        "am",
    }
)


def extract_keywords(text: str) -> list[str]:
    """Extract significant keywords from text (3+ chars, stop-words filtered)."""
    words = {
        w.lower()
        for w in re.findall(r"\b[a-z]{3,}\b", text.lower())
        if w.lower() not in _ANALYZE_STOP_WORDS
    }
    return sorted(words)
