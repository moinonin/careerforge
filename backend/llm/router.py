"""LLM provider router — Sprint 6: DB-driven adapter selection with BYOK support.

Selects adapter from:
  1. User's active LLMConfig (DB) — Sprint 6
  2. Fallback: LLM_PROVIDER env var (Sprint 3 compatibility)
"""

from __future__ import annotations

import os
from typing import Any

from backend.llm.adapter import _ADAPTERS, LLMAdapter
from backend.llm.adapters import (  # noqa: F401  (registers adapters)
    LiteLLMAdapter,
    OllamaAdapter,
    OpenAIAdapter,
)
from backend.models import LLMConfig
from backend.security import decrypt_api_key
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _ensure_registries() -> None:
    """Ensure all adapters are loaded/registered. Safe to call multiple times."""
    import backend.llm.adapters  # noqa: F401


def get_default_provider() -> str:
    """Return the default LLM provider slug.

    Reads ``LLM_PROVIDER`` env var; falls back to ``"openai"``.
    """
    _ensure_registries()
    return os.environ.get("LLM_PROVIDER", "openai").lower()


async def get_user_active_config(session: AsyncSession, user_id: str) -> LLMConfig | None:
    """Get the user's active LLM configuration, if any."""
    stmt = select(LLMConfig).where(
        LLMConfig.user_id == user_id,
        LLMConfig.is_active == True,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


def build_adapter(
    provider_slug: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
) -> LLMAdapter:
    """Instantiate the adapter for *provider_slug* (or the default).

    Raises ``ValueError`` if the provider is not registered.
    """
    _ensure_registries()

    if provider_slug is None:
        provider_slug = get_default_provider()

    cls = _ADAPTERS.get(provider_slug)
    if cls is None:
        known = ", ".join(sorted(_ADAPTERS.keys()))
        raise ValueError(
            f"Unknown LLM provider '{provider_slug}'. Known providers: {known}"
        )

    return cls(
        api_key=api_key,
        base_url=base_url,
    )


async def build_adapter_from_config(
    session: AsyncSession,
    user_id: str,
    *,
    provider_slug: str | None = None,
    model: str | None = None,
) -> tuple[LLMAdapter, str, str | None]:
    """Build an adapter from the user's active DB config.

    Returns (adapter, provider_slug, model_name).

    Falls back to env-driven defaults if no DB config exists.
    """
    # Try to get user's active config
    if provider_slug is None:
        config = await get_user_active_config(session, user_id)
        if config:
            provider_slug = config.provider
            model = config.model_name
            api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else None
            base_url = config.base_url
        else:
            # Fallback to env
            provider_slug = get_default_provider()
            api_key = None
            base_url = None
    else:
        # Explicit provider requested - still try to get config if it matches
        config = await get_user_active_config(session, user_id)
        if config and config.provider == provider_slug:
            api_key = decrypt_api_key(config.api_key_encrypted) if config.api_key_encrypted else None
            base_url = config.base_url
            if model is None:
                model = config.model_name
        else:
            api_key = None
            base_url = None

    adapter = build_adapter(
        provider_slug=provider_slug,
        api_key=api_key,
        base_url=base_url,
    )

    return adapter, provider_slug, model