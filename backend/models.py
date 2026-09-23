"""Database models — Sprint 0 skeleton (core tables only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="user", nullable=False)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    # Relationships (forward-declared; imported lazily to avoid circular refs)
    profiles = relationship("MasterProfile", back_populates="owner", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")
    llm_configs = relationship("LLMConfig", back_populates="user", cascade="all, delete-orphan")
    generation_jobs = relationship("GenerationJob", back_populates="user", cascade="all, delete-orphan")
    stored_artifacts = relationship("StoredArtifact", back_populates="user", cascade="all, delete-orphan")
    user_credits = relationship("UserCredit", back_populates="owner", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="recipient", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="actor", cascade="all, delete-orphan")
    organizations = relationship("Organization", back_populates="owner", cascade="all, delete-orphan")
    org_memberships = relationship(
        "OrganizationMember", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="OrganizationMember.user_id",
    )
    master_profiles = relationship("OrganizationMasterProfile", back_populates="created_by_user", cascade="all, delete-orphan", foreign_keys="OrganizationMasterProfile.created_by")
    usage_logs = relationship("OrganizationUsageLog", back_populates="user", cascade="all, delete-orphan", foreign_keys="OrganizationUsageLog.user_id")
    invitations = relationship("OrganizationInvitation", back_populates="invited_by_user", cascade="all, delete-orphan", foreign_keys="OrganizationInvitation.invited_by")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    metrics = relationship("GenerationMetric", back_populates="user", foreign_keys="GenerationMetric.user_id", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Master Profiles
# ---------------------------------------------------------------------------

class MasterProfile(Base):
    __tablename__ = "master_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), default="Default Master Profile", nullable=False)
    profile_data: Mapped[dict] = mapped_column(JSON, nullable=False)  # JSONB-compatible; validated by Pydantic at API layer
    master_prompt_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_draft: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False
    )

    owner = relationship("User", back_populates="profiles")


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_tier: Mapped[str] = mapped_column(String(50), nullable=False)  # trial | pay_per_use | individual | team
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # active | trialing | canceled | past_due
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    storage_quota_bytes: Mapped[int] = mapped_column(Integer, default=5_242_880, nullable=False)  # 5 MB default

    user = relationship("User", back_populates="subscription")
    organization = relationship("Organization", back_populates="subscriptions")


# ---------------------------------------------------------------------------
# LLM Configs (BYOK)
# ---------------------------------------------------------------------------

class LLMConfig(Base):
    __tablename__ = "llm_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: __import__("uuid").uuid4().hex)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # system_default | openai | anthropic | ollama | custom
    base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False
    )

    user = relationship("User", back_populates="llm_configs")


# ---------------------------------------------------------------------------
# Generation Jobs
# ---------------------------------------------------------------------------

class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    profile_id: Mapped[str] = mapped_column(String(36), ForeignKey("master_profiles.id", ondelete="SET NULL"), nullable=True, index=True)
    job_title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    job_description: Mapped[str] = mapped_column(Text, nullable=False)
    output_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)  # en, es, de, fr, fi
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending | processing | completed | failed
    cv_docx_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cv_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cl_docx_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cl_pdf_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    at_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    missing_keywords: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True
    )
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="generation_jobs")
    profile = relationship("MasterProfile", back_populates="generation_jobs")
    metric = relationship("GenerationMetric", back_populates="generation_job", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Stored Artifacts (Document Library)
# ---------------------------------------------------------------------------

class ArtifactType(str):
    CV_DOCX = "cv_docx"
    CV_PDF = "cv_pdf"
    CL_DOCX = "cl_docx"
    CL_PDF = "cl_pdf"


class StoredArtifact(Base):
    __tablename__ = "stored_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    generation_job_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("generation_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    artifact_type: Mapped[str] = mapped_column(String(20), nullable=False)
    file_key: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    at_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_temp: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user = relationship("User", back_populates="stored_artifacts")
    generation_job = relationship("GenerationJob", back_populates="stored_artifacts")


# ---------------------------------------------------------------------------
# Credit Packages (pay-per-set bundles)
# ---------------------------------------------------------------------------

class CreditPackage(Base):
    __tablename__ = "credit_packages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    stripe_product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    price_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# ---------------------------------------------------------------------------
# User Credits Ledger
# ---------------------------------------------------------------------------

class UserCredit(Base):
    __tablename__ = "user_credits"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    package_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("credit_packages.id", ondelete="SET NULL"), nullable=True, index=True)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    owner = relationship("User", back_populates="user_credits")


# ---------------------------------------------------------------------------
# Audit Log (append-only)
# ---------------------------------------------------------------------------

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    actor_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    actor = relationship("User", back_populates="audit_logs")


# ---------------------------------------------------------------------------
# Notifications (in-app)
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    recipient_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    recipient = relationship("User", back_populates="notifications")


# ---------------------------------------------------------------------------
# Email Queue (idempotent send tracking)
# ---------------------------------------------------------------------------

class EmailQueue(Base):
    __tablename__ = "email_queue"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[str] = mapped_column(String(100), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)  # pending | sent | failed
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Organizations (multi-tenancy — Sprint 7+)
# ---------------------------------------------------------------------------

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    max_seats: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    used_storage_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seat_price_cents: Mapped[int] = mapped_column(Integer, default=1200, nullable=False)  # $12/seat/month
    team_quota: Mapped[int] = mapped_column(Integer, default=250, nullable=False)
    team_quota_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quota_period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    owner = relationship("User", back_populates="organizations")
    subscriptions = relationship("Subscription", back_populates="organization", cascade="all, delete-orphan")
    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan", foreign_keys="OrganizationMember.organization_id")
    master_profiles = relationship("OrganizationMasterProfile", back_populates="organization", cascade="all, delete-orphan")
    usage_logs = relationship("OrganizationUsageLog", back_populates="organization", cascade="all, delete-orphan")
    invitations = relationship("OrganizationInvitation", back_populates="organization", cascade="all, delete-orphan")
    metrics = relationship("GenerationMetric", back_populates="organization", cascade="all, delete-orphan")


# ---------------------------------------------------------------------------
# Organization Members
# ---------------------------------------------------------------------------

class OrganizationMember(Base):
    __tablename__ = "organization_members"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)  # admin | member
    invited_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="org_memberships", foreign_keys="OrganizationMember.user_id")

    __table_args__ = (
        # unique(organization_id, user_id) enforced in migration
    )


# ---------------------------------------------------------------------------
# Organization Master Profiles (shared profile templates — Sprint 7+)
# ---------------------------------------------------------------------------

class OrganizationMasterProfile(Base):
    __tablename__ = "organization_master_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    profile_data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    is_shared: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False,
        onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization", back_populates="master_profiles")
    created_by_user = relationship("User", back_populates="master_profiles", foreign_keys="OrganizationMasterProfile.created_by")


# ---------------------------------------------------------------------------
# Organization Usage Log (team quota tracking — Sprint 7+)
# ---------------------------------------------------------------------------

class OrganizationUsageLog(Base):
    __tablename__ = "organization_usage_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    generation_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    period_key: Mapped[str] = mapped_column(String(20), nullable=False)  # YYYY-MM
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False,
        onupdate=lambda: datetime.now(UTC)
    )

    organization = relationship("Organization", back_populates="usage_logs")
    user = relationship("User", back_populates="usage_logs", foreign_keys="OrganizationUsageLog.user_id")


# ---------------------------------------------------------------------------
# Organization Invitations (team onboarding — Sprint 7+)
# ---------------------------------------------------------------------------

class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member", nullable=False)
    token: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending | accepted | expired | cancelled
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    organization = relationship("Organization", back_populates="invitations")
    invited_by_user = relationship("User", back_populates="invitations", foreign_keys="OrganizationInvitation.invited_by")


# ---------------------------------------------------------------------------
# Refresh Tokens (Sprint 1 — token rotation + revocation store)
# ---------------------------------------------------------------------------

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(511), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    user = relationship("User", back_populates="refresh_tokens")


# ---------------------------------------------------------------------------
# Profile → GenerationJob back-ref (declared on GenerationJob above)
# ---------------------------------------------------------------------------

MasterProfile.generation_jobs = relationship(
    "GenerationJob", back_populates="profile", cascade="all, delete-orphan"
)
GenerationJob.stored_artifacts = relationship(
    "StoredArtifact", back_populates="generation_job", cascade="all, delete-orphan"
)


# ---------------------------------------------------------------------------
# Generation Metrics (Sprint 10 — feature usage tracking)
# ---------------------------------------------------------------------------

class GenerationMetric(Base):
    __tablename__ = "generation_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="gen_random_uuid()")
    generation_job_id: Mapped[str] = mapped_column(String(36), ForeignKey("generation_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)  # openai | anthropic | ollama | custom
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    output_language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    export_format: Mapped[str] = mapped_column(String(10), nullable=False)  # docx | pdf | both
    at_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    generation_job = relationship("GenerationJob", back_populates="metric")
    organization = relationship("Organization", back_populates="metrics")
    user = relationship("User", back_populates="metrics", foreign_keys="GenerationMetric.user_id")
