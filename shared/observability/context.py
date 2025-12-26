from typing import Dict, Any
from dataclasses import dataclass


@dataclass(frozen=True)
class RequestContext:
    """
    Request context passed explicitly through the application.

    Immutable dataclass containing tracing information for observability.

    Fields:
    - trace_id: Global trace identifier (e.g., "t-8fa21c9d")
    - trace_source: Where the trace originated (e.g., "GAPI:/api/orders")
    - request_id: Request identifier (e.g., "r-912873")
    - request_source: Current service and endpoint (e.g., "ORDER_SERVICE:/internal/orders")
    """
    trace_id: str
    trace_source: str
    request_id: str
    request_source: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'trace_id': self.trace_id,
            'trace_source': self.trace_source,
            'request_id': self.request_id,
            'request_source': self.request_source
        }

