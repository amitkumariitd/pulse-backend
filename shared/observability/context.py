from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
import secrets
import re
from contextvars import ContextVar, Token


TRACE_ID_PATTERN = re.compile(r'^t\d{10}[0-9a-f]{12}$')
REQUEST_ID_PATTERN = re.compile(r'^r\d{10}[0-9a-f]{12}$')


# Async-safe storage for the current request context
_CURRENT_CONTEXT: ContextVar[Optional["RequestContext"]] = ContextVar(
    "current_request_context", default=None
)


def generate_trace_id() -> str:
    """
    Generate a new trace_id.

    Format: t + Unix timestamp (seconds) + 12 hexadecimal characters
    Example: t1735228800a1b2c3d4e5f6

    Returns:
        str: A unique trace_id
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)
    return f"t{timestamp}{random_hex}"


def generate_request_id() -> str:
    """
    Generate a new request_id.

    Format: r + Unix timestamp (seconds) + 12 hexadecimal characters
    Example: r1735228800f6e5d4c3b2a1

    Returns:
        str: A unique request_id
    """
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)
    return f"r{timestamp}{random_hex}"


def is_valid_trace_id(trace_id: str) -> bool:
    """
    Validate trace_id format.

    Args:
        trace_id: The trace_id to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return bool(TRACE_ID_PATTERN.match(trace_id))


def is_valid_request_id(request_id: str) -> bool:
    """
    Validate request_id format.

    Args:
        request_id: The request_id to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return bool(REQUEST_ID_PATTERN.match(request_id))


@dataclass(frozen=True)
class RequestContext:
    """
    Request context passed explicitly through the application.

    Immutable dataclass containing tracing information for observability.

    Fields:
    - trace_id: Global trace identifier (e.g., "t1735228800a1b2c3d4e5f6")
    - trace_source: Where the trace originated (e.g., "GAPI:/api/orders")
    - request_id: Request identifier (e.g., "r1735228800f6e5d4c3b2a1")
    - request_source: Current service and endpoint (e.g., "ORDER_SERVICE:/internal/orders")
    - span_source: Service call path (e.g., "GAPI:POST/api/orders->PULSE:POST/internal/orders") - for logging only, not stored in DB
    """
    trace_id: str
    trace_source: str
    request_id: str
    request_source: str
    span_source: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'trace_id': self.trace_id,
            'trace_source': self.trace_source,
            'request_id': self.request_id,
            'request_source': self.request_source,
            'span_source': self.span_source
        }


# --- ContextVar helpers for async-safe access outside route handlers ---
def set_current_context(ctx: "RequestContext") -> Token:
    """Set the current RequestContext in a ContextVar and return the reset token.

    Use this in middleware at request ingress.
    """
    return _CURRENT_CONTEXT.set(ctx)


def reset_current_context(token: Token) -> None:
    """Reset the ContextVar to its previous value using the provided token."""
    try:
        _CURRENT_CONTEXT.reset(token)
    except Exception:
        # Best-effort reset; avoid raising during shutdown/cleanup paths
        _CURRENT_CONTEXT.set(None)


def get_context_obj() -> Optional["RequestContext"]:
    """Get the current RequestContext object if available, else None."""
    return _CURRENT_CONTEXT.get()


def get_context() -> Dict[str, Any]:
    """Get the current context as a dict suitable for headers/logs.

    Returns an empty dict when no context is set (e.g., outside a request).
    """
    ctx = _CURRENT_CONTEXT.get()
    return ctx.to_dict() if ctx else {}

