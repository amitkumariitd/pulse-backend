from fastapi import Request
from starlette.types import ASGIApp, Receive, Scope, Send
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response
from .context import (
    RequestContext,
    generate_trace_id,
    generate_request_id,
    generate_span_id,
    set_current_context,
    reset_current_context,
)


class ContextMiddleware:
    """
    ASGI Middleware that creates RequestContext from headers and attaches it to request.state.

    Extracts tracing headers:
    - X-Trace-Id, X-Request-Id, X-Trace-Source, X-Request-Source
    - X-Parent-Span-Id (treated as parent_span_id)

    Generates trace_id, request_id if not provided.
    Always generates a NEW span_id for each incoming request.
    Treats incoming X-Parent-Span-Id as parent_span_id for span hierarchy tracking.
    Builds span_source by appending current request_source to parent's request_source.
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

        # Extract parent_span_id from incoming X-Parent-Span-Id header (if present)
        parent_span_id = request.headers.get('X-Parent-Span-Id')

        # Always generate NEW span_id for this service's operation
        span_id = generate_span_id()

        # Get HTTP method and path for endpoint identifier
        method = scope.get("method", "GET")
        path = scope.get("path", "/")
        endpoint_code = f"{method}{path}"
        trace_source_header = request.headers.get('X-Trace-Source')

        # Create initial context with method and path
        trace_source = trace_source_header or f"{self.service_name.upper()}:{endpoint_code}"
        request_source = f"{self.service_name.upper()}:{endpoint_code}"

        # Build span_source: if we have parent request source, append current service
        # Otherwise, just use current service
        parent_request_source = request.headers.get('X-Request-Source')
        if parent_request_source:
            span_source = f"{parent_request_source}->{request_source}"
        else:
            span_source = request_source

        ctx = RequestContext(
            trace_id=trace_id,
            trace_source=trace_source,
            request_id=request_id,
            request_source=request_source,
            span_id=span_id,
            span_source=span_source,
            parent_span_id=parent_span_id
        )

        # Attach context to scope state
        if "state" not in scope:
            scope["state"] = {}
        scope["state"]["context"] = ctx
        # Also set process-local async context for downstream utilities (e.g., HTTP client, logger)
        token = set_current_context(ctx)

        # Wrap send to add headers to response
        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                # Add tracing headers to response
                headers = list(message.get("headers", []))
                headers.append((b"x-trace-id", trace_id.encode()))
                headers.append((b"x-request-id", request_id.encode()))
                headers.append((b"x-span-id", span_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            # Ensure context is reset even if request handling fails
            reset_current_context(token)


# Backward compatibility alias
TracingMiddleware = ContextMiddleware

