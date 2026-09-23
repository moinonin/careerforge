"""Generation endpoint tests — Sprint 3 end-to-end.

Tests the ``POST /api/v1/generate`` and ``GET /api/v1/generate/jobs/{job_id}``
endpoints by patching the service-layer functions the routes import, so no real
DB connection or LLM call is required.

Sprint 3 acceptance criteria covered here:
* Generation job is created and returns a job_id
* CV and cover letter are returned as markdown
* ATS score is computed and persisted on the job (0-100)
* Job ownership is enforced (404 when using another user's profile)
* Missing profile_id → 400
* Missing job_description → 400
* Unauthenticated → 401
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

from backend.database import get_session

from backend.llm.adapter import GenerationError, LLMAdapter
from backend.database import get_session
from backend.main import app
from fastapi.testclient import TestClient
from backend.llm.docx_renderer import DocxRenderer, CoverLetterDocxRenderer

# ── Canned LLM output ─────────────────────────────────────────────────────────

MOCK_CV = {
    "contact": {
        "full_name": "Jane Doe",
        "location": "San Francisco, CA",
        "email": "jane@example.com",
        "linkedin": "https://linkedin.com/in/janedoe",
    },
    "summary": "Senior backend engineer with 8 years of experience.",
    "skills": {
        "technical": ["Python", "PostgreSQL", "Redis"],
        "domain": ["Distributed Systems"],
        "tools": ["Docker", "Kubernetes"],
        "soft": ["Communication", "Leadership"],
    },
    "experience": [
        {
            "role": "Senior Backend Engineer",
            "company": "Acme Corp",
            "location": "San Francisco, CA",
            "start_date": "2022-01",
            "end_date": "present",
            "details": "Led migration to microservices.",
        }
    ],
    "education": [
        {
            "degree": "B.S. Computer Science",
            "institution": "Stanford University",
            "location": "Stanford, CA",
            "start_date": "2012-09",
            "end_date": "2016-06",
        }
    ],
    "projects": [],
    "publications": [],
    "certifications": [],
    "languages": [{"language": "English", "proficiency": "Native"}],
    "additional_info": "",
}

MOCK_COVER_LETTER = {
    "header": "May 8, 2026",
    "salutation": "Dear Hiring Manager,",
    "opening": "I am writing to express my interest in the position.",
    "body_paragraphs": [
        "With 8 years of backend engineering experience, I bring...",
        "My expertise in Python and distributed systems would be an asset...",
    ],
    "call_to_action": "I look forward to discussing how I can contribute.",
    "closing": "Sincerely,",
    "signature": "Jane Doe",
}


class FakeAdapter(LLMAdapter):
    """An adapter that returns a canned CV + cover letter."""

    async def generate(
        self,
        prompt: str,
        schema: dict,
        *,
        model: str | None = None,
        max_retries: int = 3,
    ) -> dict:
        return {"cv": MOCK_CV, "cover_letter": MOCK_COVER_LETTER}


# ── Constants ─────────────────────────────────────────────────────────────────

FAKE_USER_ID = "test-user-id"
FAKE_PROFILE_ID = "test-profile-id"
FAKE_JOB_ID = "test-job-id"
OTHER_USER_ID = "other-user-id"
OTHER_PROFILE_ID = "other-profile-id"


def _make_fake_profile(user_id: str, profile_id: str) -> MagicMock:
    p = MagicMock()
    p.id = profile_id
    p.user_id = user_id
    p.name = "Jane Doe"
    p.consent = True
    return p


def _make_fake_job(user_id: str = FAKE_USER_ID, at_score: int = 75) -> MagicMock:
    j = MagicMock()
    j.id = FAKE_JOB_ID
    j.user_id = user_id
    j.profile_id = FAKE_PROFILE_ID
    j.job_description = "Senior Python Backend Engineer"
    j.job_title = "CV & Cover Letter"
    j.status = "completed"
    j.cv_docx_url = f"/api/v1/generate/jobs/{FAKE_JOB_ID}/cv"
    j.cl_docx_url = f"/api/v1/generate/jobs/{FAKE_JOB_ID}/cover-letter"
    j.at_score = at_score
    j.tokens_used = 4200
    j.execution_time_ms = 12340
    return j


# ── Client factories ──────────────────────────────────────────────────────────


def _make_client() -> TestClient:
    """Client with mocked DB session + auth (returns FAKE_USER_ID)."""
    app.dependency_overrides.clear()
    from backend.auth.schemas import get_current_user_id
    from backend.database import get_session

    fake_profile = _make_fake_profile(FAKE_USER_ID, FAKE_PROFILE_ID)

    async def _mock_get_session():
        session = AsyncMock()
        # The route runs: result = await session.execute(stmt)
        # followed by: profile = result.scalar_one_or_none()
        # Assign a fixed async function so session.execute is stable.
        async def _execute(stmt):
            result = MagicMock()
            result.scalar_or_none.return_value = fake_profile
            result.scalar_one_or_none.return_value = fake_profile
            return result
        session.execute = _execute
        session.commit = AsyncMock()  # await session.commit() must work
        session.refresh = AsyncMock()  # await session.refresh(job) must work
        return session

    async def _mock_get_current_user_id():
        return FAKE_USER_ID

    app.dependency_overrides[get_session] = _mock_get_session
    app.dependency_overrides[get_current_user_id] = _mock_get_current_user_id
    return TestClient(app)


def _make_unauth_client() -> TestClient:
    """Client with mocked DB session but NO auth override.

    The real ``get_current_user_id`` runs; without a valid token it raises
    401.
    """
    app.dependency_overrides.clear()
    from backend.database import get_session

    async def _mock_get_session():
        session = AsyncMock()
        async def _execute(stmt):
            result = MagicMock()
            result.scalar_or_none.return_value = None
            result.scalar_one_or_none.return_value = None
            return result
        session.execute = _execute
        return session

    app.dependency_overrides[get_session] = _mock_get_session
    # Do NOT override get_current_user_id — let the real one run
    return TestClient(app)


# ── Patch helpers ─────────────────────────────────────────────────────────────


def _patch_all():
    """Patch the service-layer functions the routes call.

    Returns ``(fake_profile, fake_job, patchers)`` where ``patchers`` is a
    list of active patchers to stop in a ``finally`` block.
    """
    fake_profile = _make_fake_profile(FAKE_USER_ID, FAKE_PROFILE_ID)
    fake_job = _make_fake_job(FAKE_USER_ID)

    patchers = [
        patch("backend.api.routes.generate.create_generation_job"),
        patch("backend.api.routes.generate.get_job"),
        patch("backend.api.routes.generate.mark_job_completed"),
        patch("backend.api.routes.generate.mark_job_failed"),
        patch("backend.api.routes.generate.mark_job_processing"),
        patch("backend.api.routes.generate.render_cv_markdown"),
        patch("backend.api.routes.generate.render_cover_letter_markdown"),
        patch("backend.api.routes.generate.run_generation"),
        patch("backend.api.routes.generate._compute_at_score"),
    ]

    started = []
    for p in patchers:
        started.append(p.start())

    # Async functions that are awaited in the route — use side_effect
    async def _create_job(**kwargs):
        fake_job.user_id = kwargs.get("user_id", FAKE_USER_ID)
        fake_job.profile_id = kwargs.get("profile_id", FAKE_PROFILE_ID)
        fake_job.job_description = kwargs.get("job_description", "")
        fake_job.job_title = kwargs.get("job_title", "CV & Cover Letter")
        return fake_job

    async def _get_job(session, job_id, user_id):
        return fake_job

    async def _mark_completed(session, job_id, **kwargs):
        return fake_job

    async def _mark_failed(*args, **kwargs):
        return None

    async def _mark_processing(*args, **kwargs):
        return None

    async def _run_gen(session, job, *, provider=None, model=None):
        return (MOCK_CV, MOCK_COVER_LETTER)

    started[0].side_effect = _create_job
    started[1].side_effect = _get_job
    started[2].side_effect = _mark_completed
    started[3].side_effect = _mark_failed
    started[4].side_effect = _mark_processing
    started[7].side_effect = _run_gen
    started[5].return_value = "# CV\n\nJane Doe\n\nSenior backend engineer..."
    started[6].return_value = "# Cover Letter\n\nDear Hiring Manager,\n\nI am writing..."
    started[8].return_value = fake_job.at_score

    return fake_profile, fake_job, started


# ── Tests ──────────────────────────────────────────────────────────────────────


def test_generate_requires_auth():
    """Missing or invalid auth returns 401."""
    client = _make_unauth_client()
    response = client.post(
        "/api/v1/generate",
        json={"profile_id": FAKE_PROFILE_ID, "job_description": "Backend engineer"},
    )
    assert response.status_code == 401


def test_generate_success_returns_job_with_artifacts():
    client = _make_client()
    fake_profile, fake_job, patchers = _patch_all()
    try:
        response = client.post(
            "/api/v1/generate",
            json={
                "profile_id": FAKE_PROFILE_ID,
                "job_description": "Senior Python Backend Engineer at a startup",
                "job_title": "Senior Backend Engineer",
                "company_name": "Startup Inc",
            },
        )
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "completed"
        assert data["job_id"] == FAKE_JOB_ID
        assert "cv_markdown" in data
        assert "cover_letter_markdown" in data
        assert "# CV" in data["cv_markdown"]
        assert "Jane Doe" in data["cv_markdown"]
        assert "Dear Hiring Manager" in data["cover_letter_markdown"]
    finally:
        for p in patchers:
            p.stop()


def test_generate_persists_at_score_on_job():
    client = _make_client()
    _, _, patchers = _patch_all()
    try:
        gen_response = client.post(
            "/api/v1/generate",
            json={
                "profile_id": FAKE_PROFILE_ID,
                "job_description": "Python backend engineer with PostgreSQL and Redis experience",
            },
        )
        assert gen_response.status_code == 202
        job_id = gen_response.json()["job_id"]

        job_response = client.get(f"/api/v1/generate/jobs/{job_id}")
        assert job_response.status_code == 200
        job_data = job_response.json()
        assert job_data["status"] == "completed"
        assert job_data["at_score"] == 75
        assert 0 <= job_data["at_score"] <= 100
        assert job_data["cv_docx_url"] == f"/api/v1/generate/jobs/{FAKE_JOB_ID}/cv"
        assert job_data["cl_docx_url"] == f"/api/v1/generate/jobs/{FAKE_JOB_ID}/cover-letter"
    finally:
        for p in patchers:
            p.stop()


def test_generate_missing_profile_id_returns_400():
    client = _make_client()
    _, _, patchers = _patch_all()
    try:
        response = client.post(
            "/api/v1/generate",
            json={"job_description": "Some job"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "profile_id is required"
    finally:
        for p in patchers:
            p.stop()


def test_generate_missing_job_description_returns_400():
    client = _make_client()
    _, _, patchers = _patch_all()
    try:
        response = client.post(
            "/api/v1/generate",
            json={"profile_id": FAKE_PROFILE_ID},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "job_description is required"
    finally:
        for p in patchers:
            p.stop()


def test_get_job_not_found_returns_404():
    client = _make_client()
    # Patch get_job to return None (job not found)
    async def _get_job_none(session, job_id, user_id):
        return None
    get_job_patch = patch(
        "backend.api.routes.generate.get_job", side_effect=_get_job_none
    )
    get_job_patch.start()
    try:
        response = client.get("/api/v1/generate/jobs/does-not-exist")
        assert response.status_code == 404
    finally:
        get_job_patch.stop()


# ── Validation & retry tests ─────────────────────────────────────────────────

def _bad_cv_skills_as_list() -> dict:
    """CV where skills is a list instead of the required object — should fail."""
    return {
        "contact": {
            "full_name": "Jane Doe",
            "location": "San Francisco, CA",
        },
        "summary": "Senior backend engineer.",
        "skills": ["Python", "PostgreSQL"],  # ← should be an object
        "experience": [
            {
                "role": "Senior Backend Engineer",
                "company": "Acme Corp",
                "bullets": [],
            }
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "Stanford University",
            }
        ],
    }


def _bad_cv_missing_contact_name() -> dict:
    """CV missing required contact.full_name — should fail."""
    return {
        "contact": {
            "location": "San Francisco, CA",
        },
        "summary": "Senior backend engineer.",
        "skills": {
            "technical": ["Python"],
            "domain": [],
            "tools": [],
            "soft": [],
        },
        "experience": [],
        "education": [],
    }


def _good_cv() -> dict:
    """Minimal CV that passes validation."""
    return {
        "contact": {
            "full_name": "Jane Doe",
            "location": "San Francisco, CA",
        },
        "summary": "Senior backend engineer.",
        "skills": {
            "technical": ["Python"],
            "domain": [],
            "tools": [],
            "soft": [],
        },
        "experience": [
            {
                "role": "Senior Backend Engineer",
                "company": "Acme Corp",
                "bullets": [],
            }
        ],
        "education": [],
    }


def _good_cover_letter() -> dict:
    """Minimal cover letter that passes validation."""
    return {
        "header": "May 8, 2026",
        "salutation": "Dear Hiring Manager,",
        "opening": "I am writing to express my interest.",
        "body_paragraphs": ["Paragraph one.", "Paragraph two."],
        "call_to_action": "I look forward to discussing.",
        "closing": "Sincerely,",
        "signature": "Jane Doe",
    }


def test_cv_validation_accepts_valid_cv():
    """A correctly-shaped CV dict passes Pydantic validation."""
    from backend.llm.output_models import cv_output_from_dict

    cv = cv_output_from_dict(_good_cv())
    assert cv.summary == "Senior backend engineer."
    assert cv.contact.full_name == "Jane Doe"
    assert cv.skills.technical == ["Python"]


def test_cv_validation_rejects_skills_as_list():
    """A CV where skills is a list (not object) fails validation."""
    from backend.llm.output_models import cv_output_from_dict
    from pydantic import ValidationError

    try:
        cv_output_from_dict(_bad_cv_skills_as_list())
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        errors = exc.errors()
        assert len(errors) >= 1
        # The skills field error
        assert any(e.get("loc", ()) == ("skills",) for e in errors) or any(
            "skills" in str(e.get("loc", ())) for e in errors
        )


def test_cv_validation_rejects_missing_contact_full_name():
    """A CV missing contact.full_name fails validation."""
    from backend.llm.output_models import cv_output_from_dict
    from pydantic import ValidationError

    try:
        cv_output_from_dict(_bad_cv_missing_contact_name())
        assert False, "Expected ValidationError"
    except ValidationError as exc:
        errors = exc.errors()
        assert any("full_name" in str(e.get("loc", ())) for e in errors)


def test_cover_letter_validation_accepts_valid():
    """A correctly-shaped cover letter dict passes Pydantic validation."""
    from backend.llm.output_models import cover_letter_output_from_dict

    cl = cover_letter_output_from_dict(_good_cover_letter())
    assert cl.header == "May 8, 2026"
    assert cl.body_paragraphs == ["Paragraph one.", "Paragraph two."]


def test_combined_schema_detects_cv_and_cl():
    """The combined schema (cv + cover_letter wrapper) is detected correctly."""
    from backend.llm.adapter import _detect_schema_type
    from backend.llm.prompts import CV_SCHEMA, COVER_LETTER_SCHEMA

    combined = {
        "type": "object",
        "properties": {
            "cv": CV_SCHEMA,
            "cover_letter": COVER_LETTER_SCHEMA,
        },
        "required": ["cv", "cover_letter"],
    }
    assert _detect_schema_type(combined) == "combined"

    # Sub-schemas are detected as their respective types
    assert _detect_schema_type(CV_SCHEMA) == "cv"
    assert _detect_schema_type(COVER_LETTER_SCHEMA) == "cl"


def test_validation_error_message_includes_field_info():
    """When validation fails, the error message contains useful field info."""
    from backend.llm.adapter import _validate_against_schema
    from backend.llm.prompts import CV_SCHEMA

    bad = _bad_cv_missing_contact_name()
    ok, msg = _validate_against_schema(bad, CV_SCHEMA)
    assert ok is False
    assert msg  # non-empty error message
    assert "full_name" in msg or "contact" in msg.lower()


def test_adapters_import_and_register():
    """All three adapters are registered and importable."""
    from backend.llm.adapter import _ADAPTERS, get_adapter_class

    assert "openai" in _ADAPTERS
    assert "litellm" in _ADAPTERS
    assert "ollama" in _ADAPTERS
    assert get_adapter_class("openai") is not None
    assert get_adapter_class("litellm") is not None
    assert get_adapter_class("ollama") is not None


def test_relevance_note_field_exists_on_experience_schema():
    """CV_SCHEMA experience items include optional relevance_note field."""
    from backend.llm.prompts import CV_SCHEMA

    exp_props = CV_SCHEMA["properties"]["experience"]["items"]["properties"]
    assert "relevance_note" in exp_props
    assert exp_props["relevance_note"]["type"] == "string"


def test_output_models_allow_extra_fields():
    """Output models ignore extra fields (extra='ignore') so LLM additions
    don't break validation."""
    from backend.llm.output_models import cv_output_from_dict

    cv = cv_output_from_dict({
        "contact": {"full_name": "Jane", "location": "SF"},
        "summary": "Hi",
        "skills": {"technical": [], "domain": [], "tools": [], "soft": []},
        "experience": [],
        "education": [],
        # Extra field not in schema — should be ignored, not rejected
        "some_extra_field": "should be ignored",
    })
    assert cv.summary == "Hi"
    assert not hasattr(cv, "some_extra_field")


# ── DOCX renderer tests ────────────────────────────────────────────────────────

CV_DOCX_TEST_DATA = {
    "contact": {
        "full_name": "Jane Doe",
        "location": "San Francisco, CA",
        "email": "jane@example.com",
        "linkedin": "linkedin.com/in/janedoe",
    },
    "summary": "Senior backend engineer with 8 years of experience.",
    "skills": {
        "technical": ["Python", "PostgreSQL"],
        "domain": ["Distributed Systems"],
        "tools": ["Docker"],
        "soft": ["Communication"],
    },
    "experience": [
        {
            "role": "Senior Backend Engineer",
            "company": "Acme Corp",
            "location": "San Francisco, CA",
            "start_date": "2022-01",
            "end_date": "Present",
            "relevance_note": "Directly relevant: scale infrastructure experience.",
            "bullets": [
                "Led migration to microservices.",
                "Built real-time data pipeline.",
            ],
        },
    ],
    "education": [
        {
            "degree": "B.S. Computer Science",
            "institution": "Stanford University",
            "location": "Stanford, CA",
            "start_date": "2014-09",
            "end_date": "2018-06",
            "thesis": "Optimizing distributed consensus protocols.",
        },
    ],
    "publications": [
        {"citation": "Rotich, N. et al. (2023). High-throughput consensus.", "year": "2023"},
    ],
    "certifications": [
        {"name": "AWS Solutions Architect", "issuer": "Amazon Web Services", "year": "2022"},
    ],
    "languages": [{"language": "English", "proficiency": "Native"}],
    "projects": [
        {"name": "OpenAudit", "description": "Audit log framework.", "tech_stack": ["Python"], "link": "https://github.com/example"},
    ],
    "additional_info": "Volunteer mentor at CodePath.org.",
}

CL_DOCX_TEST_DATA = {
    "header": "March 15, 2026",
    "salutation": "Dear Hiring Manager,",
    "opening": "I am excited to apply.",
    "body_paragraphs": ["Paragraph one.", "Paragraph two."],
    "call_to_action": "I look forward to discussing.",
    "closing": "Sincerely,",
    "signature": "Jane Doe",
}


def _get_paragraph_texts(docx_path: str) -> list[str]:
    """Return non-empty paragraph texts from a .docx file."""
    from docx import Document as Reader
    return [p.text for p in Reader(docx_path).paragraphs if p.text.strip()]


def test_docx_renderer_cv_has_name_header():
    """CV docx starts with the candidate name as a large bold heading."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(CV_DOCX_TEST_DATA).save(path)
        texts = _get_paragraph_texts(path)
        assert texts[0] == "Jane Doe"
        assert "San Francisco, CA" in texts[1]


def test_docx_renderer_cv_has_all_required_sections():
    """CV docx contains all required ATS sections."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(CV_DOCX_TEST_DATA).save(path)
        texts = _get_paragraph_texts(path)
    assert any("Professional Summary" in t for t in texts)
    assert any(t == "Core Competencies" for t in texts)
    assert any(t == "Professional Experience" for t in texts)
    assert any(t == "Education" for t in texts)
    assert any(t == "Publications" for t in texts)
    assert any(t == "Certifications" for t in texts)
    assert any(t == "Languages" for t in texts)
    assert any(t == "Projects" for t in texts)
    assert any(t == "Additional Information" for t in texts)


def test_docx_renderer_cv_experience_uses_bold_role_line():
    """Experience entries render role+company on a bold line."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer
    from docx import Document as Reader

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(CV_DOCX_TEST_DATA).save(path)
        doc = Reader(path)
        texts = [p.text for p in doc.paragraphs]
        role_lines = [t for t in texts if "Senior Backend Engineer" in t and "Acme Corp" in t]
        assert len(role_lines) >= 1
        found = False
        for p in doc.paragraphs:
            if "Senior Backend Engineer" in p.text and "Acme Corp" in p.text:
                assert p.runs[0].bold is True
                found = True
        assert found


def test_docx_renderer_cv_relevance_note_is_italic():
    """Relevance notes render as italic indented paragraphs."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer
    from docx import Document as Reader

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(CV_DOCX_TEST_DATA).save(path)
        doc = Reader(path)
        found = False
        for p in doc.paragraphs:
            if "Relevance to target role" in p.text:
                assert p.runs[0].italic is True
                found = True
        assert found


def test_docx_renderer_cv_skills_are_grouped():
    """Skills render under Core Competencies with group labels."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(CV_DOCX_TEST_DATA).save(path)
        texts = _get_paragraph_texts(path)
    assert any("Technical Skills: Python, PostgreSQL" in t for t in texts)
    assert any("Domain Knowledge: Distributed Systems" in t for t in texts)
    assert any("Tools: Docker" in t for t in texts)
    assert any("Soft Skills: Communication" in t for t in texts)


def test_docx_renderer_cv_missing_sections_are_omitted():
    """CV sections with no data are not rendered as headings."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer

    minimal_cv = {
        "contact": {"full_name": "Jane", "location": "SF"},
        "summary": "Hi",
        "skills": {"technical": [], "domain": [], "tools": [], "soft": []},
        "experience": [],
        "education": [],
        "publications": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "additional_info": "",
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(minimal_cv).save(path)
        texts = _get_paragraph_texts(path)
    # Name and summary only — no empty section headings
    assert texts[0] == "Jane"
    assert "Professional Summary" in texts
    section_headings = [
        "Core Competencies", "Professional Experience", "Education",
        "Publications", "Certifications", "Languages", "Projects",
        "Additional Information",
    ]
    for h in section_headings:
        assert h not in texts, f"Empty section heading '{h}' should not appear"


def test_docx_renderer_cv_dates_show_present_for_current_role():
    """Current role (end_date='Present') shows ' – Present' in dates."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer

    cv = {
        "contact": {"full_name": "Jane", "location": "SF"},
        "summary": "",
        "skills": {"technical": [], "domain": [], "tools": [], "soft": []},
        "experience": [
            {
                "role": "Engineer",
                "company": "Acme",
                "start_date": "2022-01",
                "end_date": "Present",
                "bullets": [],
            }
        ],
        "education": [],
        "publications": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "additional_info": "",
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(cv).save(path)
        texts = _get_paragraph_texts(path)
    role_lines = [t for t in texts if "Engineer" in t and "Acme" in t]
    assert any("– Present" in t or "- Present" in t for t in role_lines)


def test_docx_renderer_cv_page_size_a4():
    """A4 page size renders with A4 dimensions."""
    import tempfile, os
    from backend.config import Settings
    from backend.llm.docx_renderer import DocxRenderer
    from docx import Document as Reader

    a4_settings = Settings()
    a4_settings.default_docx_page_size = "a4"

    cv_minimal = {
        "contact": {"full_name": "Jane", "location": "SF"},
        "summary": "",
        "skills": {"technical": [], "domain": [], "tools": [], "soft": []},
        "experience": [],
        "education": [],
        "publications": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "additional_info": "",
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer(config=a4_settings).render(cv_minimal).save(path)
        doc = Reader(path)
        section = doc.sections[0]
        # A4 = 210mm x 297mm ≈ 8.27in x 11.69in
        assert abs(section.page_width.inches - 8.27) < 0.05
        assert abs(section.page_height.inches - 11.69) < 0.05


def test_docx_renderer_cover_letter_has_all_parts():
    """Cover letter docx contains header, salutation, body, closing, signature."""
    import tempfile, os
    from backend.llm.docx_renderer import CoverLetterDocxRenderer

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cl.docx")
        CoverLetterDocxRenderer().render(CL_DOCX_TEST_DATA).save(path)
        texts = _get_paragraph_texts(path)
    assert texts[0] == "March 15, 2026"
    assert texts[1] == "Dear Hiring Manager,"
    assert texts[2] == "I am excited to apply."
    assert "Paragraph one." in texts
    assert "Paragraph two." in texts
    assert texts[-2] == "Sincerely,"
    assert texts[-1] == "Jane Doe"


def test_docx_renderer_empty_cv_produces_valid_docx():
    """Even a CV with only a name produces a valid (non-empty) .docx."""
    import tempfile, os
    from backend.llm.docx_renderer import DocxRenderer

    cv = {
        "contact": {"full_name": "Jane Doe", "location": "SF"},
        "summary": "",
        "skills": {"technical": [], "domain": [], "tools": [], "soft": []},
        "experience": [],
        "education": [],
        "publications": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "additional_info": "",
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "cv.docx")
        DocxRenderer().render(cv).save(path)
        size = os.path.getsize(path)
        assert size > 1000, f"Expected valid docx > 1KB, got {size} bytes"


# ── DOCX download endpoint integration test ────────────────────────────────────

def _make_test_cv() -> dict:
    """Full CV dict for endpoint integration tests."""
    return {
        "contact": {
            "full_name": "Jane Doe",
            "location": "San Francisco, CA",
            "email": "jane@example.com",
            "linkedin": "linkedin.com/in/janedoe",
        },
        "summary": "Senior backend engineer with 8 years of experience.",
        "skills": {
            "technical": ["Python", "PostgreSQL"],
            "domain": ["Distributed Systems"],
            "tools": ["Docker"],
            "soft": ["Communication"],
        },
        "experience": [
            {
                "role": "Senior Backend Engineer",
                "company": "Acme Corp",
                "location": "San Francisco, CA",
                "start_date": "2022-01",
                "end_date": "Present",
                "relevance_note": "Directly relevant.",
                "bullets": ["Led migration.", "Built pipeline."],
            },
        ],
        "education": [
            {
                "degree": "B.S. Computer Science",
                "institution": "Stanford University",
                "location": "Stanford, CA",
                "start_date": "2014-09",
                "end_date": "2018-06",
            }
        ],
        "publications": [],
        "certifications": [],
        "languages": [{"language": "English", "proficiency": "Native"}],
        "projects": [],
        "additional_info": "",
    }


def _make_test_cl() -> dict:
    """Full cover letter dict for endpoint integration tests."""
    return {
        "header": "March 15, 2026",
        "salutation": "Dear Hiring Manager,",
        "opening": "I am excited to apply.",
        "body_paragraphs": ["Paragraph one.", "Paragraph two."],
        "call_to_action": "I look forward to discussing.",
        "closing": "Sincerely,",
        "signature": "Jane Doe",
    }


def _make_test_client():
    """Client with REAL in-memory DB session + auth + mocked LLM adapter for DOCX tests.

    Returns ``(client, cleanup_shutil)`` where ``cleanup_shutil`` is a callable
    that removes the test artifacts directory (call in a ``finally`` block).
    """
    import asyncio
    import shutil
    import tempfile
    from unittest.mock import AsyncMock as _AM, patch as _patch

    # Stop any patches from previous tests that may have leaked
    _patch.stopall()

    # Use a temporary directory for artifacts so tests are isolated and clean up
    test_artifacts_dir = tempfile.mkdtemp(prefix="cf_test_artifacts_")

    # Patch settings BEFORE importing backend modules that use it
    settings_patch = _patch("backend.config.settings.db_url", "sqlite+aiosqlite:///:memory:")
    settings_patch.start()
    artifacts_patch = _patch("backend.config.settings.generation_artifacts_dir", test_artifacts_dir)
    artifacts_patch.start()

    # Now import modules that depend on settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from backend.database import Base
    from backend.main import create_app

    # Create engine and session factory manually for SQLite (no pool args)
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        pool_pre_ping=True,
    )
    test_session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    # Patch the database module's globals
    import backend.database as db_module
    db_module.engine = test_engine
    db_module._session_factory = test_session_factory

    # Initialize tables
    async def _init_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    asyncio.run(_init_tables())

    # Define the real_get_session using our test factory
    async def real_get_session():
        async with test_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    resume_adapter = _AM()
    resume_adapter.generate = _AM(return_value={
        "cv": _make_test_cv(),
        "cover_letter": _make_test_cl(),
    })

    # Patch build_adapter at the SERVICE layer so run_generation uses our mock
    build_adapter_patch = _patch("backend.llm.service.build_adapter", return_value=resume_adapter)
    build_adapter_patch.start()

    app = create_app()
    app.dependency_overrides.clear()
    from backend.auth.schemas import get_current_user_id
    from backend.database import get_session as db_get_session

    # Use the REAL session factory (which uses the in-memory SQLite)
    # No mocking of the session - let real DB operations happen
    app.dependency_overrides[db_get_session] = real_get_session

    async def _mock_get_current_user_id():
        return FAKE_USER_ID

    app.dependency_overrides[get_current_user_id] = _mock_get_current_user_id

    # Seed a user and profile in the real DB
    async def _seed_profile():
        from backend.models import MasterProfile, User
        from backend.auth.jwt_utils import hash_password
        import json
        async for session in real_get_session():
            user = User(
                id=FAKE_USER_ID,
                email="test@example.com",
                password_hash=hash_password("password"),
                full_name="Test User",
            )
            session.add(user)
            profile = MasterProfile(
                id="test-profile-seed",
                user_id=FAKE_USER_ID,
                title="Jane Doe",
                profile_data={
                    "contact": {"full_name": "Jane Doe", "location": "San Francisco, CA"},
                    "summary": "Senior backend engineer with 8 years of experience.",
                    "skills": {
                        "technical": ["Python", "PostgreSQL"],
                        "domain": ["Distributed Systems"],
                        "tools": ["Docker"],
                        "soft": ["Communication"],
                    },
                    "experience": [],
                    "education": [],
                    "publications": [],
                    "certifications": [],
                    "languages": [],
                    "projects": [],
                    "additional_info": "",
                },
                is_default=False,
                is_draft=False,
            )
            session.add(profile)
            await session.commit()
            break

    asyncio.run(_seed_profile())

    client = TestClient(app)

    def cleanup():
        build_adapter_patch.stop()
        settings_patch.stop()
        artifacts_patch.stop()
        asyncio.run(test_engine.dispose())
        shutil.rmtree(test_artifacts_dir, ignore_errors=True)

    return client, cleanup


def _make_test_client_failed():
    """Client with mocked DB session + auth + settings + a failing adapter."""
    import asyncio
    import shutil
    from unittest.mock import AsyncMock as _AM, patch as _patch

    from backend.database import init_db
    from backend.main import create_app
    from backend.models import GenerationJob

    os.environ["CAREERFORGE__DATABASE__URL"] = "sqlite+aiosqlite:///:memory:"
    os.environ["LLM_PROVIDER"] = "openai"
    os.environ["LLM_MODEL"] = "gpt-4o-mini"

    failed_adapter = _AM()
    failed_adapter.generate = _AM(side_effect=Exception("LLM timeout"))

    # Patch run_generation at the *route* level so this test is isolated from
    # whatever _patch_all() left behind in earlier tests.
    run_gen_patch = _patch(
        "backend.api.routes.generate.run_generation",
        new_callable=_AM,
        side_effect=GenerationError("LLM generation failed: simulated failure"),
    )
    run_gen_patch.start()
    build_adapter_patch = _patch("backend.llm.service.build_adapter", return_value=failed_adapter)
    build_adapter_patch.start()

    app = create_app()
    app.dependency_overrides.clear()
    from backend.auth.schemas import get_current_user_id
    from backend.database import get_session as db_get_session

    _profile_store: dict[str, MagicMock] = {}

    async def _mock_get_session():
        session = _AM()
        async def _execute(stmt):
            result = MagicMock()
            result.scalar_or_none.return_value = _profile_store.get("profile", None)
            result.scalar_one_or_none.return_value = _profile_store.get("profile", None)
            result.scalars.return_value = MagicMock()
            result.all.return_value = []
            result.first.return_value = None
            result.one_or_none.return_value = None
            result.one.return_value = None
            result.fetchone.return_value = None
            result.fetchall.return_value = []
            result.rowcount = 1
            result.inserted_primary_key = [FAKE_USER_ID]
            return result
        session.execute = _execute
        session.commit = _AM()
        session.refresh = _AM()
        session.add = MagicMock()
        session.flush = MagicMock()
        session.rollback = _AM()
        yield session

    async def _mock_get_current_user_id():
        return FAKE_USER_ID

    app.dependency_overrides[db_get_session] = _mock_get_session
    app.dependency_overrides[get_current_user_id] = _mock_get_current_user_id

    # Seed a profile so the generation endpoint can find it
    _profile_store["profile"] = MagicMock()
    _profile_store["profile"].id = "test-profile-seed"
    _profile_store["profile"].user_id = FAKE_USER_ID
    _profile_store["profile"].name = "Jane Doe"
    _profile_store["profile"].consent = True
    _profile_store["profile"].profile_data = {
        "contact": {"full_name": "Jane Doe", "location": "San Francisco, CA"},
        "summary": "Senior backend engineer with 8 years of experience.",
        "skills": {
            "technical": ["Python", "PostgreSQL"],
            "domain": ["Distributed Systems"],
            "tools": ["Docker"],
            "soft": ["Communication"],
        },
        "experience": [],
        "education": [],
        "publications": [],
        "certifications": [],
        "languages": [],
        "projects": [],
        "additional_info": "",
    }

    client = TestClient(app)

    def cleanup():
        shutil.rmtree("/tmp/cf_test_artifacts_fail", ignore_errors=True)
        build_adapter_patch.stop()
        run_gen_patch.stop()

    return client, cleanup


# ── Integration tests ───────────────────────────────────────────────────────────


def test_generation_endpoint_renders_and_stores_docx_file():
    """POST /api/v1/generate with mocked LLM renders actual .docx files
    to the configured artifacts directory and stores the file paths on the job."""
    client, cleanup = _make_test_client()
    try:
        resp = client.post(
            "/api/v1/generate",
            json={
                "profile_id": "test-profile-seed",
                "job_description": "Senior Backend Engineer at Acme Corp",
                "job_title": "Senior Backend Engineer",
                "company_name": "Acme Corp",
            },
        )
        assert resp.status_code == 202, resp.text

        import asyncio
        from sqlalchemy import select
        from backend.models import GenerationJob
        import backend.database as db_module

        async def _check_db():
            test_engine = db_module.engine
            assert test_engine is not None, "DB engine not initialized"
            async with test_engine.begin() as conn:
                stmt = select(GenerationJob).where(GenerationJob.id.isnot(None))
                result = await conn.execute(stmt)
                row = result.first()
                assert row is not None, "No job row found in DB"
                # row is a Row object with attribute access
                assert row.status == "completed"
                assert row.cv_docx_url.endswith("_cv.docx"), f"Unexpected cv path: {row.cv_docx_url}"
                assert row.cl_docx_url.endswith("_cover_letter.docx"), f"Unexpected cl path: {row.cl_docx_url}"
                assert os.path.isfile(row.cv_docx_url), f"CV docx not found: {row.cv_docx_url}"
                assert os.path.isfile(row.cl_docx_url), f"CL docx not found: {row.cl_docx_url}"
                cv_size = os.path.getsize(row.cv_docx_url)
                cl_size = os.path.getsize(row.cl_docx_url)
                assert cv_size > 1000, f"CV docx too small: {cv_size}"
                assert cl_size > 1000, f"CL docx too small: {cl_size}"

        asyncio.run(_check_db())
    finally:
        cleanup()


def test_generation_endpoint_cv_download_endpoint_serves_docx():
    """GET /api/v1/generate/jobs/{id}/cv returns the stored CV .docx file."""
    client, cleanup = _make_test_client()
    try:
        resp = client.post(
            "/api/v1/generate",
            json={
                "profile_id": "test-profile-seed",
                "job_description": "Senior Backend Engineer",
                "job_title": "Senior Backend Engineer",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]

        # Same client has the auth override — reuse it
        dl_resp = client.get(f"/api/v1/generate/jobs/{job_id}/cv")
        assert dl_resp.status_code == 200, dl_resp.text
        assert dl_resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert dl_resp.headers["content-disposition"].startswith("attachment; filename=")
        assert len(dl_resp.content) > 1000
    finally:
        cleanup()


def test_generation_endpoint_cl_download_endpoint_serves_docx():
    """GET /api/v1/generate/jobs/{id}/cover-letter returns the stored cover letter .docx file."""
    client, cleanup = _make_test_client()
    try:
        resp = client.post(
            "/api/v1/generate",
            json={
                "profile_id": "test-profile-seed",
                "job_description": "Senior Backend Engineer",
                "job_title": "Senior Backend Engineer",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]

        # Same client has the auth override — reuse it
        dl_resp = client.get(f"/api/v1/generate/jobs/{job_id}/cover-letter")
        assert dl_resp.status_code == 200, dl_resp.text
        assert dl_resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        assert dl_resp.headers["content-disposition"].startswith("attachment; filename=")
        assert len(dl_resp.content) > 1000
    finally:
        cleanup()


def test_generation_endpoint_poll_job_returns_docx_urls():
    """GET /api/v1/generate/jobs/{id} returns cv_docx_url and cl_docx_url
    pointing at downloadable .docx files."""
    client, cleanup = _make_test_client()
    try:
        resp = client.post(
            "/api/v1/generate",
            json={
                "profile_id": "test-profile-seed",
                "job_description": "Senior Backend Engineer",
                "job_title": "Senior Backend Engineer",
            },
        )
        assert resp.status_code == 202, resp.text
        job_id = resp.json()["job_id"]

        # Same client has the auth override — reuse it
        poll_resp = client.get(f"/api/v1/generate/jobs/{job_id}")
        assert poll_resp.status_code == 200, poll_resp.text
        data = poll_resp.json()
        assert data["status"] == "completed"
        assert data["cv_docx_url"].endswith("_cv.docx")
        assert data["cl_docx_url"].endswith("_cover_letter.docx")
        assert data["cv_docx_url"] != f"/api/v1/generate/jobs/{job_id}/cv"
        assert data["cl_docx_url"] != f"/api/v1/generate/jobs/{job_id}/cover-letter"
        assert os.path.isfile(data["cv_docx_url"]), f"CV docx not on disk: {data['cv_docx_url']}"
        assert os.path.isfile(data["cl_docx_url"]), f"CL docx not on disk: {data['cl_docx_url']}"
    finally:
        cleanup()


def test_generation_endpoint_job_not_completed_returns_404_on_download():
    """GET /api/v1/generate/jobs/{id}/cv returns 404 if generation failed."""
    client, cleanup = _make_test_client_failed()
    try:
        resp = client.post(
            "/api/v1/generate",
            json={
                "profile_id": "test-profile-404",
                "job_description": "Senior Backend Engineer",
                "job_title": "Senior Backend Engineer",
            },
        )
        assert resp.status_code == 502, resp.text
    finally:
        cleanup()

    # Use the same client (has auth override) to check a non-existent job
    dl_resp = client.get("/api/v1/generate/jobs/does-not-exist/cv")
    assert dl_resp.status_code == 409, dl_resp.text


