import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .context import set_context, clear_context, get_context


def generate_id(prefix: str) -> str:
    """Generate a unique ID with given prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class ContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts request context from headers and makes it available
    throughout the request lifecycle via contextvars.

    Extracts:
    - Tracing: X-Trace-Id, X-Request-Id, X-Trace-Source, X-Request-Source
    - Identity: X-User-Id, X-Client-Id
    - Domain: X-Order-Id, X-Account-Id

    Generates trace_id and request_id if not provided.
    """

    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name

    async def dispatch(self, request: Request, call_next):
        # Extract or generate tracing context
        trace_id = request.headers.get('X-Trace-Id') or generate_id('t')
        request_id = request.headers.get('X-Request-Id') or generate_id('r')

        endpoint = f"{request.url.path}"
        trace_source = request.headers.get('X-Trace-Source') or f"{self.service_name.upper()}:{endpoint}"
        request_source = f"{self.service_name.upper()}:{endpoint}"

        # Extract identity context
        user_id = request.headers.get('X-User-Id')
        client_id = request.headers.get('X-Client-Id')

        # Extract domain context
        order_id = request.headers.get('X-Order-Id')
        account_id = request.headers.get('X-Account-Id')

        # Set all context
        set_context(
            trace_id=trace_id,
            trace_source=trace_source,
            request_id=request_id,
            request_source=request_source,
            user_id=user_id,
            client_id=client_id,
            order_id=order_id,
            account_id=account_id
        )

        # Process request
        response = await call_next(request)

        # Add tracing headers to response
        response.headers['X-Trace-Id'] = trace_id
        response.headers['X-Request-Id'] = request_id

        # Cleanup context
        clear_context()

        return response


# Backward compatibility alias
TracingMiddleware = ContextMiddleware

