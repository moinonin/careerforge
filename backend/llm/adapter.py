"""LLM Adapter — abstract interface + concrete implementations.

Sprint 3: Unified LLM Adapter.

Usage::
    adapter = get_adapter(config)
    result = adapter.generate(prompt=..., schema=cv_schema)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.llm.output_models import (
    cover_letter_output_from_dict,
    cv_output_from_dict,
)

# ── Abstract interface ───────────────────────────────────────────────────────


class LLMAdapter(ABC):
    """Contract every LLM provider adapter must satisfy.

    Subclasses ``__init__`` SHOULD accept ``api_key: str | None`` and
    ``base_url: str | None`` and pass them through to ``super().__init__``
    so the provider router can instantiate any adapter uniformly.
    """

    def __init__(self, api_key: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        schema: dict[str, Any],
        *,
        model: str | None = None,
        max_retries: int = 3,
    ) -> dict[str, Any]:
        """Call the LLM with *prompt* and return a dict that validates
        against *schema* (CV_SCHEMA or COVER_LETTER_SCHEMA).

        Retries up to *max_retries* times on parse/validation failure,
        appending the validation error to the prompt on each attempt.
        """


class GenerationError(Exception):
    """Raised when all retry attempts fail."""

    def __init__(self, message: str, last_error: Exception | None = None):
        super().__init__(message)
        self.last_error = last_error


# ── Provider registry ────────────────────────────────────────────────────────


# Mapping of provider slug → adapter class.  Populated at module load.
_ADAPTERS: dict[str, type[LLMAdapter]] = {}


def register_adapter(provider: str):
    """Decorator that registers an adapter class under *provider*."""

    def decorator(cls: type[LLMAdapter]) -> type[LLMAdapter]:
        _ADAPTERS[provider] = cls
        return cls

    return decorator


def get_adapter_class(provider: str) -> type[LLMAdapter] | None:
    """Return the adapter class for *provider*, or ``None``."""
    return _ADAPTERS.get(provider)


# ── Validation helpers ────────────────────────────────────────────────────────

def _detect_schema_type(schema: dict[str, Any]) -> str:
    """Return which output model to use for *schema*.

    ``'cv'`` → CVOutput, ``'cl'`` → CoverLetterOutput,
    ``'combined'`` → top-level wrapper (cv + cover_letter keys),
    ``'unknown'`` → no match.
    """
    props = schema.get("properties", {})
    if "cv" in props and "cover_letter" in props:
        return "combined"
    if "summary" in props and "contact" in props:
        return "cv"
    if "header" in props and "salutation" in props:
        return "cl"
    return "unknown"


def _validate_against_schema(data: Any, schema: dict[str, Any]) -> tuple[bool, str]:
    """Return ``(True, '')`` if *data* matches *schema*, else ``(False, msg)``.

    Uses Pydantic output models for real nested validation — not the
    hand-rolled checks that missed most of the schema.
    """
    if not isinstance(data, dict):
        return False, f"Expected a JSON object, got {type(data).__name__}"

    schema_type = _detect_schema_type(schema)

    if schema_type == "combined":
        # Top-level wrapper: check cv and cover_letter keys exist,
        # then delegate sub-object validation to the caller / adapter.
        missing = [k for k in ("cv", "cover_letter") if k not in data]
        if missing:
            return False, f"Missing required top-level keys: {', '.join(missing)}"
        return True, ""

    if schema_type == "cv":
        try:
            cv_output_from_dict(data)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    if schema_type == "cl":
        try:
            cover_letter_output_from_dict(data)
            return True, ""
        except Exception as exc:
            return False, str(exc)

    # Unknown schema — fall back to required-key check only
    required = schema.get("required", [])
    for key in required:
        if key not in data:
            return False, f"Missing required field: {key}"
    return True, ""


def _build_retry_prompt(base_prompt: str, schema: dict[str, Any], last_error: str) -> str:
    """Append a correction instruction to *base_prompt* for a retry attempt."""
    return (
        f"{base_prompt}\n\n"
        f"--- PREVIOUS ATTEMPT FAILED ---\n"
        f"The previous response could not be parsed. Error: {last_error}\n"
        f"Please re-generate the response, ensuring it is valid JSON matching "
        f"the required schema with no extra text, markdown fences, or commentary.\n"
        f"Output ONLY the JSON object."
    )
