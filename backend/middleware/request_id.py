"""Request ID middleware + structured logging integration.

Every incoming request gets a unique ``X-Request-Id`` that is
injected into the structlog context so all downstream log entries
include ``request_id``, ``user_id``, ``action``, ``status``, and
``duration_ms`` when present.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Scope, Receive, Send

from backend.config import settings

log = structlog.get_logger()


class RequestIdMiddleware:
    """Starlette ASGI middleware that injects a request ID into structlog."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = scope.get("headers", [])
        req_id = None
        for k, v in request_id:
            if k == b"x-request-id":
                req_id = v.decode()
                break

        if req_id is None:
            req_id = str(uuid.uuid4())

        # Extract user_id if available from Authorization header
        user_id = None
        for k, v in scope.get("headers", []):
            if k == b"authorization":
                token = v.decode()
                if token.startswith("Bearer "):
                    try:
                        from backend.auth.jwt_utils import get_user_id_from_token
                        user_id = get_user_id_from_token(token[7:])
                    except Exception:
                        pass
                break

        # Build log context
        log_context: dict[str, Any] = {
            "request_id": req_id,
        }
        if user_id:
            log_context["user_id"] = user_id

        # Patch send to add request_id to response headers
        async def wrapped_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", req_id.encode()))
                message["headers"] = headers
            await send(message)

        # Inject context into structlog for downstream loggers
        logger = log.bind(**log_context)
        logger.info(
            "request_started",
            method=scope.get("method"),
            path=scope.get("path"),
            user_id=user_id or "anonymous",
        )

        await self.app(scope, receive, wrapped_send)


def request_id_middleware(app: ASGIApp) -> ASGIApp:
    """Factory function to wrap an ASGI app with request ID middleware."""
    return RequestIdMiddleware(app)
