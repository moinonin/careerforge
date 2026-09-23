"""Security headers middleware.

Adds Content-Security-Policy, HSTS, X-Frame-Options,
X-Content-Type-Options, and Referrer-Policy to every response.
"""

from __future__ import annotations

from starlette.types import ASGIApp, Scope, Receive, Send

from backend.config import settings


class SecurityHeadersMiddleware:
    """Starlette ASGI middleware that injects security headers."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def wrapped_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"x-frame-options", b"DENY"))
                headers.append((b"referrer-policy", b"strict-origin-when-cross-origin"))
                headers.append(
                    (b"content-security-policy", b"default-src 'self'")
                )
                if settings.environment == "production":
                    headers.append(
                        (
                            b"strict-transport-security",
                            b"max-age=31536000; includeSubDomains",
                        )
                    )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, wrapped_send)


def security_headers_middleware(app: ASGIApp) -> ASGIApp:
    """Factory function to wrap an ASGI app with security headers."""
    return SecurityHeadersMiddleware(app)
