from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from .context import RequestContext, generate_trace_id, generate_request_id


class ContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that creates RequestContext from headers and attaches it to request.state.

    Extracts tracing headers:
    - X-Trace-Id, X-Request-Id, X-Trace-Source, X-Request-Source

    Generates trace_id and request_id if not provided.
    """

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        # Extract or generate tracing IDs
        trace_id = request.headers.get('X-Trace-Id') or generate_trace_id()
        request_id = request.headers.get('X-Request-Id') or generate_request_id()

        endpoint = f"{request.url.path}"
        trace_source = request.headers.get('X-Trace-Source') or f"{self.service_name.upper()}:{endpoint}"
        request_source = f"{self.service_name.upper()}:{endpoint}"

        # Create RequestContext object
        ctx = RequestContext(
            trace_id=trace_id,
            trace_source=trace_source,
            request_id=request_id,
            request_source=request_source
        )

        # Attach context to request state
        request.state.context = ctx

        # Process request
        response = await call_next(request)

        # Add tracing headers to response
        response.headers['X-Trace-Id'] = trace_id
        response.headers['X-Request-Id'] = request_id

        return response


# Backward compatibility alias
TracingMiddleware = ContextMiddleware

