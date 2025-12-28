from typing import Dict, Any
from dataclasses import dataclass
import time
import secrets
import re


TRACE_ID_PATTERN = re.compile(r'^t\d{10}[0-9a-f]{12}$')
REQUEST_ID_PATTERN = re.compile(r'^r\d{10}[0-9a-f]{12}$')
SPAN_ID_PATTERN = re.compile(r'^s[0-9a-f]{8}$')


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


def generate_span_id() -> str:
    """
    Generate a new span_id.

    Format: s + 8 hexadecimal characters
    Example: sa1b2c3d4

    Returns:
        str: A unique span_id
    """
    random_hex = secrets.token_hex(4)
    return f"s{random_hex}"


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


def is_valid_span_id(span_id: str) -> bool:
    """
    Validate span_id format.

    Args:
        span_id: The span_id to validate

    Returns:
        bool: True if valid, False otherwise
    """
    return bool(SPAN_ID_PATTERN.match(span_id))


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
    - span_id: Span identifier for this operation (e.g., "sa1b2c3d4")
    - span_source: Service call path (e.g., "GAPI:POST/api/orders->PULSE:POST/internal/orders")
    """
    trace_id: str
    trace_source: str
    request_id: str
    request_source: str
    span_id: str
    span_source: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'trace_id': self.trace_id,
            'trace_source': self.trace_source,
            'request_id': self.request_id,
            'request_source': self.request_source,
            'span_id': self.span_id,
            'span_source': self.span_source
        }

