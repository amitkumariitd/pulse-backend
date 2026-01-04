"""Access log middleware for structured JSON logging."""

import time
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request as StarletteRequest
from .logger import get_logger

logger = get_logger("access")


class AccessLogMiddleware:
    """
    ASGI Middleware that logs HTTP requests in structured JSON format.
    
    Logs include:
    - HTTP method and path
    - Status code
    - Response time
    - Client IP
    - Request context (trace_id, request_id, etc.)
    """

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = StarletteRequest(scope)
        start_time = time.time()
        status_code = 500  # Default to 500 if response never starts

        async def send_with_logging(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_with_logging)
        finally:
            # Calculate response time
            duration_ms = (time.time() - start_time) * 1000

            # Get context from scope if available
            ctx = scope.get("state", {}).get("context")

            # Get client IP
            client_host = "unknown"
            if scope.get("client"):
                client_host = scope["client"][0]

            # Log the access
            logger.info(
                "HTTP request completed",
                ctx,
                data={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": round(duration_ms, 2),
                    "client_ip": client_host,
                }
            )

