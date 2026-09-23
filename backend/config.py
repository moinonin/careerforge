from __future__ import annotations

import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the CareerForge backend.

    All values are read from environment variables with the ``CAREERFORGE_``
    prefix.  Set ``CAREERFORGE_CONFIG_FILE`` to override the .env search path.
    """

    model_config = SettingsConfigDict(
        env_prefix="CAREERFORGE_",
        env_nested_delimiter="__",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ─────────────────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    environment: str = "development"  # development | staging | production
    cors_origins: list[str] = []  # e.g. ["http://localhost:3000"]

    # ── Database ─────────────────────────────────────────────────────────────
    db_url: str = "postgresql+asyncpg://careerforge:careerforge@localhost:5432/careerforge"
    db_echo: bool = False

    # ── Redis / Celery ───────────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"
    broker_url: str = "redis://localhost:6379/0"
    result_backend: str = "redis://localhost:6379/0"

    # ── LLM providers ────────────────────────────────────────────────────────
    default_llm_provider: str = "openai"
    default_llm_model: str = "gpt-4o-mini"
    openai_api_key: str | None = None  # managed key (platform default)
    anthropic_api_key: str | None = None

    # ── Encryption / KMS ─────────────────────────────────────────────────────
    encryption_key_id: str | None = None  # KMS key id / arn (production)

    # ── Storage (S3 / MinIO) ─────────────────────────────────────────────────
    s3_endpoint_url: str | None = None  # e.g. http://localhost:9000 (MinIO)
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_bucket_name: str = "careerforge-documents"
    s3_region: str = "us-east-1"

    # ── Email (transactional) ────────────────────────────────────────────────
    email_provider: str = "resend"  # resend | sendgrid | postmark | ses
    email_api_key: str | None = None
    email_from_address: str = "noreply@careerforge.ai"
    email_from_name: str = "CareerForge AI"

    # ── Stripe ───────────────────────────────────────────────────────────
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_publishable_key: str | None = None
    stripe_individual_price_id: str | None = None
    stripe_team_price_id: str | None = None
    stripe_success_url: str = "https://careerforge.ai/billing"
    stripe_cancel_url: str = "https://careerforge.ai/billing"

    # ── JWT ──────────────────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── Rate limiting (Redis sliding window) ─────────────────────────────
    rate_limit_trial_generations_per_minute: int = 1
    rate_limit_paid_generations_per_minute: int = 60

    # ── Generated docs ───────────────────────────────────────────────────────
    default_docx_page_size: str = "letter"  # letter | a4
    default_docx_font: str = "Calibri"
    default_docx_font_size: int = 11
    default_docx_margin_inches: float = 1.0  # 1 inch margins all sides
    default_docx_line_spacing: float = 1.15
    default_docx_name_font_size: int = 22  # candidate name heading size (pt)
    generation_artifacts_dir: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "artifacts"
    )


settings = Settings()
