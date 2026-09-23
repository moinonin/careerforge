"""LLM provider router — picks the right adapter from env config.

Sprint 3: no ``llm_provider_configs`` table yet (arrives Sprint 6).
Adapter selection is via ``LLM_PROVIDER`` env var, falling back to ``"openai"``.
"""

from __future__ import annotations

import os

from backend.llm.adapter import _ADAPTERS, LLMAdapter
from backend.llm.adapters import (  # noqa: F401  (registers adapters)
    LiteLLMAdapter,
    OllamaAdapter,
    OpenAIAdapter,
)


def _ensure_registries() -> None:
    """Ensure all adapters are loaded/registered.  Safe to call multiple times."""
    import backend.llm.adapters  # noqa: F401


def get_default_provider() -> str:
    """Return the default LLM provider slug.

    Reads ``LLM_PROVIDER`` env var; falls back to ``"openai"``.
    """
    _ensure_registries()
    return os.environ.get("LLM_PROVIDER", "openai").lower()


def build_adapter(
    provider_slug: str | None = None,
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

    # Per-provider env config
    api_key: str | None = None
    base_url: str | None = None

    env_key_map = {
        "openai": "OPENAI_API_KEY",
        "litellm": "LiteLLM_API_KEY",
        "ollama": None,
    }
    env_base_map = {
        "openai": "OPENAI_BASE_URL",
        "litellm": "LiteLLM_BASE_URL",
        "ollama": "OLLAMA_BASE_URL",
    }

    if provider_slug in env_key_map and env_key_map[provider_slug]:
        api_key = os.environ.get(env_key_map[provider_slug])  # type: ignore[arg-type]
    if provider_slug in env_base_map and env_base_map[provider_slug]:
        base_url = os.environ.get(env_base_map[provider_slug])  # type: ignore[arg-type]

    return cls(
        api_key=api_key,
        base_url=base_url,
    )
