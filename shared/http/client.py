import httpx
from typing import Optional, Dict, Any
from shared.observability.context import get_context


class ContextPropagatingClient:
    """
    HTTP client that automatically propagates request context via headers.

    Automatically adds headers for:
    - Tracing: X-Trace-Id, X-Request-Id, X-Trace-Source, X-Request-Source
    - Span: X-Span-Id (current span, becomes parent_span_id in receiving service), X-Span-Source

    The receiving service will:
    - Read X-Span-Id as parent_span_id
    - Generate a NEW span_id for its own operation
    - Build span hierarchy for distributed tracing

    Usage:
        client = ContextPropagatingClient("http://localhost:8001")
        response = await client.post("/internal/orders", json=order_data)
        # Context headers automatically included
    """
    
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
    
    def _add_context_headers(self, headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Add context to headers."""
        headers = headers or {}
        context = get_context()

        # Map context fields to HTTP headers
        header_mapping = {
            'trace_id': 'X-Trace-Id',
            'trace_source': 'X-Trace-Source',
            'request_id': 'X-Request-Id',
            'request_source': 'X-Request-Source',
            'span_id': 'X-Span-Id',
            'span_source': 'X-Span-Source'
        }

        for ctx_key, header_key in header_mapping.items():
            if ctx_key in context and context[ctx_key]:
                headers[header_key] = context[ctx_key]

        return headers
    
    async def get(self, path: str, **kwargs) -> httpx.Response:
        """GET request with auto-propagated context."""
        kwargs['headers'] = self._add_context_headers(kwargs.get('headers'))
        return await self.client.get(path, **kwargs)
    
    async def post(self, path: str, **kwargs) -> httpx.Response:
        """POST request with auto-propagated context."""
        kwargs['headers'] = self._add_context_headers(kwargs.get('headers'))
        return await self.client.post(path, **kwargs)
    
    async def put(self, path: str, **kwargs) -> httpx.Response:
        """PUT request with auto-propagated context."""
        kwargs['headers'] = self._add_context_headers(kwargs.get('headers'))
        return await self.client.put(path, **kwargs)
    
    async def patch(self, path: str, **kwargs) -> httpx.Response:
        """PATCH request with auto-propagated context."""
        kwargs['headers'] = self._add_context_headers(kwargs.get('headers'))
        return await self.client.patch(path, **kwargs)
    
    async def delete(self, path: str, **kwargs) -> httpx.Response:
        """DELETE request with auto-propagated context."""
        kwargs['headers'] = self._add_context_headers(kwargs.get('headers'))
        return await self.client.delete(path, **kwargs)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

