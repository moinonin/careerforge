"""Error handling middleware — custom 404 and 500 responses."""

from __future__ import annotations

from starlette.responses import HTMLResponse, JSONResponse
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

        async def wrapped_send(message: dict) -> None:
            if message["type"] == "http.response.start":
                # Check for error status codes
                status_code = message.get("status", 200)
                if status_code >= 500:
                    await self._send_error_page(scope, receive, send, status_code, "500")
                    return
            await send(message)

        await self.app(scope, receive, wrapped_send)

    async def _send_error_page(self, scope: Scope, receive: Receive, send: Send, status_code: int, title: str) -> None:
        """Send a static error HTML page."""
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

        response = HTMLResponse(content=html, status_code=status_code)
        await response(scope, receive, send)


def error_handler_middleware(app: ASGIApp) -> ASGIApp:
    """Factory to wrap an ASGI app with error handling."""
    return ErrorHandlerMiddleware(app)
