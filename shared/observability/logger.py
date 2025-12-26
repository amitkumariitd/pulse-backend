import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional, Dict
from .context import get_context


# Security: Keys that should never be logged
FORBIDDEN_KEYS = {
    'authorization', 'token', 'password', 'secret',
    'api_key', 'bearer', 'jwt', 'credential', 'auth'
}


class StructuredLogger:
    """
    Structured JSON logger that automatically injects request context.

    Context is automatically included from contextvars:
    - trace_id, trace_source
    - request_id, request_source
    - user_id, client_id
    - order_id, account_id
    - metadata

    Usage:
        logger = get_logger("my_service")
        logger.info("Order created", data={"instrument": "NSE:RELIANCE"})
        # Context automatically included in log output
    """

    def __init__(self, service_name: str):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('%(message)s'))
        self.logger.addHandler(handler)
        self.logger.propagate = False

    def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove forbidden keys for security."""
        return {
            k: v for k, v in kwargs.items()
            if k.lower() not in FORBIDDEN_KEYS
        }

    def _log(self, level: str, message: str, **kwargs):
        """
        Internal log method that auto-injects context.

        Priority (later overrides earlier):
        1. Base fields (timestamp, level, service, message)
        2. Auto-injected context from contextvars
        3. User-provided kwargs
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": level,
            "service": self.service_name,
            "message": message
        }

        # Auto-inject context from contextvars
        context = get_context()
        log_entry.update(context)

        # Sanitize and merge user-provided kwargs
        safe_kwargs = self._sanitize_kwargs(kwargs)
        log_entry.update(safe_kwargs)

        # Output JSON
        log_line = json.dumps(log_entry)

        log_method = getattr(self.logger, level.lower())
        log_method(log_line)

    def debug(self, message: str, **kwargs):
        """Log debug message with auto-injected context."""
        self._log("DEBUG", message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with auto-injected context."""
        self._log("INFO", message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with auto-injected context."""
        self._log("WARNING", message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with auto-injected context."""
        self._log("ERROR", message, **kwargs)

    def critical(self, message: str, **kwargs):
        """Log critical message with auto-injected context."""
        self._log("CRITICAL", message, **kwargs)


def get_logger(service_name: str) -> StructuredLogger:
    """Get a structured logger for the given service."""
    return StructuredLogger(service_name)

