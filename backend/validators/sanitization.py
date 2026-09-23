"""Input sanitization layer.

All user-provided text passes through ``sanitize_text`` before it
enters the database or is injected into an LLM prompt.  The function
strips control characters, removes HTML/script tags, enforces a
maximum length, and returns an empty string if nothing remains.
"""

from __future__ import annotations

import re


# Characters allowed after stripping control chars: printable ASCII + common Unicode
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_HTML_TAG_RE = re.compile(r"<[^>]*>")


def sanitize_text(text: str | None, max_len: int = 10_000) -> str:
    """Sanitize a user-provided string.

    - Strip control characters (keeps ``\\n``, ``\\t``, ``\\r``).
    - Remove HTML/XML tags.
    - Truncate to ``max_len`` characters.
    - Returns an empty string if nothing remains after sanitization.
    """
    if not text:
        return ""

    cleaned = str(text)
    # Strip control characters (keep newline, tab, carriage return)
    cleaned = _CONTROL_CHAR_RE.sub("", cleaned)
    # Strip HTML tags
    cleaned = _HTML_TAG_RE.sub("", cleaned)
    # Truncate to max length
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len]

    return cleaned.strip()


def sanitize_profile_data(profile_data: dict) -> dict:
    """Sanitize all string fields in a profile_data dict.

    Recursively walks the dict and sanitizes string values.
    Non-string values are passed through unchanged.
    """
    if not isinstance(profile_data, dict):
        return profile_data

    result: dict = {}
    for key, value in profile_data.items():
        if isinstance(value, str):
            result[key] = sanitize_text(value)
        elif isinstance(value, list):
            result[key] = [
                sanitize_text(item) if isinstance(item, str) else item
                for item in value
            ]
        elif isinstance(value, dict):
            result[key] = sanitize_profile_data(value)
        else:
            result[key] = value
    return result


def validate_length(text: str, field_name: str, max_len: int = 10_000) -> None:
    """Raise ValueError if text exceeds max_len."""
    if len(text) > max_len:
        raise ValueError(
            f"{field_name} exceeds maximum length of {max_len} characters"
        )
