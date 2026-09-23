"""Input sanitization tests."""

from __future__ import annotations

import pytest

from backend.validators.sanitization import sanitize_profile_data, sanitize_text, validate_length


# ── sanitize_text ───────────────────────────────────────────────

def test_sanitize_text_returns_empty_for_none():
    assert sanitize_text(None) == ""

def test_sanitize_text_returns_empty_for_empty():
    assert sanitize_text("") == ""

def test_sanitize_text_strips_control_chars():
    text = "Hello\x00\x01\x02World\x1f"
    result = sanitize_text(text)
    assert "\x00" not in result
    assert "\x01" not in result
    assert "\x1f" not in result
    assert "HelloWorld" in result

def test_sanitize_text_strips_leading_trailing_whitespace():
    # strip() at end removes \r from end
    assert sanitize_text("  hello  ") == "hello"
    assert sanitize_text("\r\nhello\r\n") == "hello"

def test_sanitize_text_preserves_newlines_and_tabs():
    text = "Hello\n\tWorld"
    result = sanitize_text(text)
    assert "\n" in result
    assert "\t" in result

def test_sanitize_text_strips_html_tags():
    text = "Hello <script>alert('xss')</script> World"
    result = sanitize_text(text)
    assert "<script>" not in result
    assert "</script>" not in result
    # Content between tags may remain since regex only strips tags
    assert "alert" in result  # text content preserved

def test_sanitize_text_truncates():
    long_text = "A" * 20000
    result = sanitize_text(long_text, max_len=100)
    assert len(result) == 100

def test_sanitize_text_preserves_unicode():
    text = "Héllo Wörld"
    assert sanitize_text(text) == "Héllo Wörld"

def test_sanitize_text_max_len_default():
    text = "x" * 5
    assert sanitize_text(text) == text

def test_sanitize_text_strips_html_and_keeps_text():
    text = "<b>bold</b> and <i>italic</i>"
    result = sanitize_text(text)
    assert "<b>" not in result
    assert "<i>" not in result
    assert "bold" in result
    assert "italic" in result


# ── sanitize_profile_data ───────────────────────────────────────

def test_sanitize_profile_data_passes_through_non_strings():
    data = {"age": 30, "active": True, "score": 3.14}
    result = sanitize_profile_data(data)
    assert result == data

def test_sanitize_profile_data_sanitizes_strings():
    data = {"name": "<script>alert(1)</script>", "bio": "Hello\x00World"}
    result = sanitize_profile_data(data)
    assert "<script>" not in result["name"]
    assert "\x00" not in result["bio"]

def test_sanitize_profile_data_handles_nested():
    data = {"contact": {"email": "<b>test</b>"}, "skills": ["Python", "<html>"]}
    result = sanitize_profile_data(data)
    assert "<b>" not in result["contact"]["email"]
    assert "<html>" not in result["skills"][1]

def test_sanitize_profile_data_handles_lists():
    data = {"items": ["a\x00", "b<script>", "c"]}
    result = sanitize_profile_data(data)
    assert "\x00" not in result["items"][0]
    assert "<script>" not in result["items"][1]
    assert result["items"][2] == "c"


# ── validate_length ─────────────────────────────────────────────

def test_validate_length_passes():
    validate_length("hello", "test", max_len=10)

def test_validate_length_fails():
    with pytest.raises(ValueError):
        validate_length("a" * 100, "test", max_len=50)

def test_validate_length_at_limit():
    validate_length("a" * 50, "test", max_len=50)  # should not raise
