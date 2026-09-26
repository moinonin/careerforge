"""Error handling middleware — custom 404 and 500 responses."""

from __future__ import annotations

from starlette.types import ASGIApp, Scope, Receive, Send

from backend.config import settings


class ErrorHandlerMiddleware:
    """Starlette ASGI middleware that catches unhandled errors
    and returns appropriate error responses."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["path"] not in ("/", "/health", "/ready", "/docs", "/redoc", "/openapi.json"):
            pass  # only handle known routes

        _error_sent = False

        async def wrapped_send(message: dict) -> None:
            nonlocal _error_sent
            if _error_sent:
                return
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                if status_code >= 500:
                    _error_sent = True
                    await self._send_error_page(send, status_code, "500")
                    return
            await send(message)

        try:
            await self.app(scope, receive, wrapped_send)
        except Exception as exc:
            if not _error_sent:
                _error_sent = True
                await self._send_error_page(send, 500, "500")

    async def _send_error_page(self, send: Send, status_code: int, title: str) -> None:
        """Send a static error HTML page directly as ASGI messages."""
        import os

        error_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "templates", "errors",
        )
        error_file = os.path.join(error_dir, f"{status_code}.html")

        if os.path.exists(error_file):
            with open(error_file, "r") as f:
                html = f.read()
        else:
            html = f"<html><body><h1>{title}</h1></body></html>"

        body = html.encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"text/html; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
            ],
        })
        await send({"type": "http.response.body", "body": body})


def error_handler_middleware(app: ASGIApp) -> ASGIApp:
    """Factory to wrap an ASGI app with error handling."""
    return ErrorHandlerMiddleware(app)
