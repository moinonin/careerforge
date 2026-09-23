"""Security headers middleware tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from backend.middleware.security_headers import SecurityHeadersMiddleware
from backend.config import settings


def _make_app():
    """Create an async app that calls the wrapped_send callback."""
    async def app(scope, receive, send):
        # Send a response start message
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b""})
    return app


async def test_security_headers_added_to_response():
    """All security headers are present in the response."""
    middleware = SecurityHeadersMiddleware(_make_app())
    received_messages = []

    async def capture_send(message):
        received_messages.append(message)

    scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
    await middleware(scope, None, capture_send)

    response_start = [m for m in received_messages if m.get("type") == "http.response.start"]
    assert len(response_start) >= 1
    headers = response_start[0].get("headers", [])
    header_dict = {k.decode(): v.decode() for k, v in headers}

    assert header_dict["x-content-type-options"] == "nosniff"
    assert header_dict["x-frame-options"] == "DENY"
    assert header_dict["referrer-policy"] == "strict-origin-when-cross-origin"
    assert header_dict["content-security-policy"] == "default-src 'self'"


async def test_security_headers_dev_mode_no_hsts():
    """HSTS is not added in development mode."""
    with patch.object(settings, "environment", "development"):
        middleware = SecurityHeadersMiddleware(_make_app())
        received_messages = []

        async def capture_send(message):
            received_messages.append(message)

        scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
        await middleware(scope, None, capture_send)

        response_start = [m for m in received_messages if m.get("type") == "http.response.start"]
        headers = response_start[0].get("headers", [])
        header_dict = {k.decode(): v.decode() for k, v in headers}

        assert "strict-transport-security" not in header_dict


async def test_security_headers_production_includes_hsts():
    """HSTS is added in production mode."""
    with patch.object(settings, "environment", "production"):
        middleware = SecurityHeadersMiddleware(_make_app())
        received_messages = []

        async def capture_send(message):
            received_messages.append(message)

        scope = {"type": "http", "method": "GET", "path": "/", "headers": []}
        await middleware(scope, None, capture_send)

        response_start = [m for m in received_messages if m.get("type") == "http.response.start"]
        headers = response_start[0].get("headers", [])
        header_dict = {k.decode(): v.decode() for k, v in headers}

        assert header_dict["strict-transport-security"] == "max-age=31536000; includeSubDomains"
