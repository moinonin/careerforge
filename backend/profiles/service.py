from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import models
from backend.profiles import schemas

# ── Profile CRUD ─────────────────────────────────────────────────────────────


async def list_profiles(
    session: AsyncSession,
    user_id: str,
) -> list[dict[str, Any]]:
    """Return all profiles for a user, sorted by updated_at desc."""
    stmt = (
        select(models.MasterProfile)
        .where(models.MasterProfile.user_id == user_id)
        .order_by(models.MasterProfile.updated_at.desc())
    )
    result = await session.execute(stmt)
    profiles = result.scalars().all()
    out: list[dict[str, Any]] = []
    for p in profiles:
        pd = _load_profile_data(p.profile_data)
        out.append({
            "id": p.id,
            "title": p.title,
            "profile_data": pd,
            "master_prompt_text": p.master_prompt_text,
            "is_default": p.is_default,
            "is_draft": p.is_draft,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            "completeness_score": schemas.compute_completeness(
                schemas.MasterProfileData.model_validate(pd)
            ),
        })
    return out


async def get_profile(
    session: AsyncSession,
    profile_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Retrieve a single profile, ensuring ownership."""
    stmt = (
        select(models.MasterProfile)
        .where(
            and_(
                models.MasterProfile.id == profile_id,
                models.MasterProfile.user_id == user_id,
            )
        )
        .options(selectinload(models.MasterProfile.owner))
    )
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")
    pd = _load_profile_data(profile.profile_data)
    return {
        "id": profile.id,
        "title": profile.title,
        "profile_data": pd,
        "master_prompt_text": profile.master_prompt_text,
        "is_default": profile.is_default,
        "is_draft": profile.is_draft,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "completeness_score": schemas.compute_completeness(
            schemas.MasterProfileData.model_validate(pd)
        ),
        "owner": {
            "id": profile.owner.id,
            "email": profile.owner.email,
            "full_name": profile.owner.full_name,
        } if profile.owner else None,
    }


async def create_profile(
    session: AsyncSession,
    user_id: str,
    request: schemas.ProfileCreateRequest,
) -> dict[str, Any]:
    """Create a new master profile."""
    pd = schemas.profile_data_to_dict(request.profile_data)
    profile = models.MasterProfile(
        id=str(uuid4()),
        user_id=user_id,
        title=request.title,
        profile_data=pd,
        is_default=False,
        is_draft=False,
    )
    session.add(profile)
    await session.flush()
    await session.commit()
    await session.refresh(profile)
    return {
        "id": profile.id,
        "title": profile.title,
        "profile_data": pd,
        "is_default": profile.is_default,
        "is_draft": profile.is_draft,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "completeness_score": schemas.compute_completeness(request.profile_data),
    }


async def update_profile(
    session: AsyncSession,
    profile_id: str,
    user_id: str,
    request: schemas.ProfileUpdateRequest,
) -> dict[str, Any]:
    """Full update of a profile."""
    profile = await _get_owned_profile(session, profile_id, user_id)
    if request.title is not None:
        profile.title = request.title
    if request.profile_data is not None:
        profile.profile_data = schemas.profile_data_to_dict(request.profile_data)
    if request.is_default is not None:
        if request.is_default:
            await _clear_default(session, user_id)
        profile.is_default = request.is_default
    if request.is_draft is not None:
        profile.is_draft = request.is_draft
    await session.flush()
    await session.refresh(profile)
    pd = _load_profile_data(profile.profile_data)
    return {
        "id": profile.id,
        "title": profile.title,
        "profile_data": pd,
        "master_prompt_text": profile.master_prompt_text,
        "is_default": profile.is_default,
        "is_draft": profile.is_draft,
        "created_at": profile.created_at.isoformat() if profile.created_at else None,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "completeness_score": schemas.compute_completeness(
            schemas.MasterProfileData.model_validate(pd)
        ),
    }


async def patch_section(
    session: AsyncSession,
    profile_id: str,
    user_id: str,
    section_name: str,
    request: schemas.ProfileSectionPatchRequest,
) -> dict[str, Any]:
    """Patch a single section of a profile (live editor)."""
    if section_name not in schemas.VALID_SECTIONS:
        raise ValueError(f"Invalid section name: {section_name}")

    profile = await _get_owned_profile(session, profile_id, user_id)

    # Load current profile_data as dict
    current: dict[str, Any] = _load_profile_data(profile.profile_data)

    # Apply the patch for the requested section
    section_fields: dict[str, Any] = request.model_dump(exclude_unset=True, exclude_none=True)
    section_value = section_fields.get(section_name)
    if section_value is not None:
        current[section_name] = schemas.profile_data_to_dict(section_value)

    # Re-validate the full profile_data
    validated = schemas.MasterProfileData.model_validate(current)
    profile.profile_data = schemas.profile_data_to_dict(validated)
    await session.flush()
    await session.refresh(profile)

    pd = _load_profile_data(profile.profile_data)
    return {
        "id": profile.id,
        "title": profile.title,
        "profile_data": pd,
        "is_default": profile.is_default,
        "is_draft": profile.is_draft,
        "updated_at": profile.updated_at.isoformat() if profile.updated_at else None,
        "completeness_score": schemas.compute_completeness(validated),
    }


async def delete_profile(
    session: AsyncSession,
    profile_id: str,
    user_id: str,
) -> None:
    """Hard delete a profile."""
    profile = await _get_owned_profile(session, profile_id, user_id)
    await session.delete(profile)
    await session.flush()


async def set_default_profile(
    session: AsyncSession,
    profile_id: str,
    user_id: str,
) -> dict[str, Any]:
    """Mark a profile as the default for the user."""
    profile = await _get_owned_profile(session, profile_id, user_id)
    await _clear_default(session, user_id)
    profile.is_default = True
    await session.flush()
    await session.refresh(profile)
    return {
        "id": profile.id,
        "title": profile.title,
        "is_default": True,
    }


# ── Helper: skills autocomplete suggestions ──────────────────────────────────


SKILLS_TAXONOMY: list[tuple[str, str]] = [
    ("Python", "technical"),
    ("Java", "technical"),
    ("JavaScript", "technical"),
    ("TypeScript", "technical"),
    ("C++", "technical"),
    ("C#", "technical"),
    ("Go", "technical"),
    ("Rust", "technical"),
    ("Ruby", "technical"),
    ("PHP", "technical"),
    ("Swift", "technical"),
    ("Kotlin", "technical"),
    ("SQL", "technical"),
    ("HTML/CSS", "technical"),
    ("React", "technical"),
    ("Angular", "technical"),
    ("Vue.js", "technical"),
    ("Node.js", "technical"),
    ("Django", "technical"),
    ("Flask", "technical"),
    ("FastAPI", "technical"),
    ("Spring Boot", "technical"),
    ("Express.js", "technical"),
    ("TensorFlow", "technical"),
    ("PyTorch", "technical"),
    ("scikit-learn", "technical"),
    ("Pandas", "technical"),
    ("NumPy", "technical"),
    ("Docker", "technical"),
    ("Kubernetes", "technical"),
    ("AWS", "technical"),
    ("GCP", "technical"),
    ("Azure", "technical"),
    ("Git", "technical"),
    ("CI/CD", "technical"),
    ("Linux", "technical"),
    ("Bash", "technical"),
    ("PowerShell", "technical"),
    ("Machine Learning", "domain"),
    ("Deep Learning", "domain"),
    ("Data Science", "domain"),
    ("Data Engineering", "domain"),
    ("DevOps", "domain"),
    ("Cloud Architecture", "domain"),
    ("Cybersecurity", "domain"),
    ("Financial Analysis", "domain"),
    ("Risk Management", "domain"),
    ("Quantitative Analysis", "domain"),
    ("Software Architecture", "domain"),
    ("System Design", "domain"),
    ("API Design", "domain"),
    ("Database Design", "domain"),
    ("Distributed Systems", "domain"),
    ("Microservices", "domain"),
    ("Agile", "domain"),
    ("Scrum", "domain"),
    ("Product Management", "domain"),
    ("Project Management", "domain"),
    ("Process Modeling", "domain"),
    ("Separation Technology", "domain"),
    ("CFD Simulation", "domain"),
    ("Pharmaceutical Manufacturing", "domain"),
    ("Clinical Research", "domain"),
    ("Regulatory Compliance", "domain"),
    ("GMP", "domain"),
    ("ISO 9001", "domain"),
    ("GitHub", "tools"),
    ("GitLab", "tools"),
    ("Jira", "tools"),
    ("Confluence", "tools"),
    ("Jenkins", "tools"),
    ("GitHub Actions", "tools"),
    ("CircleCI", "tools"),
    ("Ansible", "tools"),
    ("Terraform", "tools"),
    ("Prometheus", "tools"),
    ("Grafana", "tools"),
    ("Elasticsearch", "tools"),
    ("Kibana", "tools"),
    ("PostgreSQL", "tools"),
    ("MySQL", "tools"),
    ("MongoDB", "tools"),
    ("Redis", "tools"),
    ("Kafka", "tools"),
    ("RabbitMQ", "tools"),
    ("Airflow", "tools"),
    ("Spark", "tools"),
    ("Hadoop", "tools"),
    ("Tableau", "tools"),
    ("Power BI", "tools"),
    ("Excel", "tools"),
    ("Jupyter", "tools"),
    ("VS Code", "tools"),
    ("IntelliJ IDEA", "tools"),
    ("PyCharm", "tools"),
    ("Windows Server", "tools"),
    ("ANSYS", "tools"),
    ("MATLAB", "tools"),
    ("Simulink", "tools"),
    ("Leadership", "soft"),
    ("Mentorship", "soft"),
    ("Cross-functional Coordination", "soft"),
    ("Communication", "soft"),
    ("Presentation Skills", "soft"),
    ("Problem Solving", "soft"),
    ("Critical Thinking", "soft"),
    ("Team Collaboration", "soft"),
    ("Stakeholder Management", "soft"),
    ("Adaptability", "soft"),
    ("Time Management", "soft"),
    ("Decision Making", "soft"),
    ("Negotiation", "soft"),
    ("Conflict Resolution", "soft"),
    ("Strategic Thinking", "soft"),
    ("Creativity", "soft"),
    ("Attention to Detail", "soft"),
    ("Self-motivation", "soft"),
    ("Remote Work", "soft"),
    ("Documentation", "soft"),
    ("Training", "soft"),
]


def get_skill_suggestions(query: str, limit: int = 20) -> list[dict[str, str]]:
    """Return skill autocomplete suggestions matching *query*."""
    if not query.strip():
        return []
    q = query.lower()
    results: list[dict[str, str]] = []
    for skill, category in SKILLS_TAXONOMY:
        if q in skill.lower():
            results.append({"skill": skill, "category": category})
        if len(results) >= limit:
            break
    return results


# ── Internal helpers ─────────────────────────────────────────────────────────


async def _get_owned_profile(
    session: AsyncSession,
    profile_id: str,
    user_id: str,
) -> models.MasterProfile:
    stmt = select(models.MasterProfile).where(
        and_(
            models.MasterProfile.id == profile_id,
            models.MasterProfile.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError("Profile not found")
    return profile


async def _clear_default(
    session: AsyncSession,
    user_id: str,
) -> None:
    """Unset the current default profile for a user."""
    stmt = select(models.MasterProfile).where(
        and_(
            models.MasterProfile.user_id == user_id,
            models.MasterProfile.is_default.is_(True),
        )
    )
    result = await session.execute(stmt)
    current = result.scalar_one_or_none()
    if current is not None:
        current.is_default = False
        await session.flush()


def _load_profile_data(raw: Any) -> dict[str, Any]:
    """Deserialize profile_data from DB (could be Text str or already dict) to dict."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            result: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return {}
        return result
    return {}
