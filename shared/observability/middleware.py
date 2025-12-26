from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from .context import RequestContext, generate_trace_id, generate_request_id


class ContextMiddleware:
    """
    ASGI Middleware that creates RequestContext from headers and attaches it to request.state.

    Extracts tracing headers:
    - X-Trace-Id, X-Request-Id, X-Trace-Source, X-Request-Source

    Generates trace_id and request_id if not provided.
    Uses route.operation_id for endpoint code if available.
    """

    def __init__(self, app: ASGIApp, service_name: str):
        self.app = app
        self.service_name = service_name

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Create request to access headers
        request = StarletteRequest(scope)

        # Extract or generate tracing IDs
        trace_id = request.headers.get('X-Trace-Id') or generate_trace_id()
        request_id = request.headers.get('X-Request-Id') or generate_request_id()

        # Get HTTP method and path for endpoint identifier
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        endpoint_code = f"{method}{path}"
        trace_source_header = request.headers.get('X-Trace-Source')

        # Create initial context with method and path
        trace_source = trace_source_header or f"{self.service_name.upper()}:{endpoint_code}"
        request_source = f"{self.service_name.upper()}:{endpoint_code}"

        ctx = RequestContext(
            trace_id=trace_id,
            trace_source=trace_source,
            request_id=request_id,
            request_source=request_source
        )

        # Attach context to scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["context"] = ctx

        # Wrap send to add headers to response
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                # Add tracing headers to response
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode()))
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)


# Backward compatibility alias
TracingMiddleware = ContextMiddleware

