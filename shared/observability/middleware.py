import uuid
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from .context import set_trace_context, clear_trace_context, get_trace_context


def generate_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str):
        super().__init__(app)
        self.service_name = service_name
    
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get('X-Trace-Id') or generate_id('t')
        request_id = request.headers.get('X-Request-Id') or generate_id('r')
        
        endpoint = f"{request.url.path}"
        trace_source = request.headers.get('X-Trace-Source') or f"{self.service_name.upper()}:{endpoint}"
        request_source = f"{self.service_name.upper()}:{endpoint}"
        
        set_trace_context(
            trace_id=trace_id,
            trace_source=trace_source,
            request_id=request_id,
            request_source=request_source
        )
        
        response = await call_next(request)
        
        response.headers['X-Trace-Id'] = trace_id
        response.headers['X-Request-Id'] = request_id
        
        clear_trace_context()
        
        return response

