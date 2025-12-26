import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional, Dict
from .context import RequestContext


# Security: Keys that should never be logged
FORBIDDEN_KEYS = {
    'authorization', 'token', 'password', 'secret',
    'api_key', 'bearer', 'jwt', 'credential', 'auth'
}


class StructuredLogger:
    """
    Structured JSON logger that accepts RequestContext explicitly.

    Usage:
        logger = get_logger("my_service")
        logger.info("Order created", ctx, data={"instrument": "NSE:RELIANCE"})
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

    def _log(self, level: str, message: str, ctx: Optional[RequestContext] = None, **kwargs):
        """
        Internal log method.

        Priority (later overrides earlier):
        1. Base fields (timestamp, level, service, message)
        2. Context fields (if ctx provided)
        3. User-provided kwargs
        """
        # Base log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "level": level,
            "service": self.service_name,
            "message": message
        }

        # Include context if provided
        if ctx:
            log_entry.update(ctx.to_dict())

        # Sanitize and merge user-provided kwargs
        safe_kwargs = self._sanitize_kwargs(kwargs)
        log_entry.update(safe_kwargs)

        # Output JSON
        log_line = json.dumps(log_entry)

        log_method = getattr(self.logger, level.lower())
        log_method(log_line)

    def debug(self, message: str, ctx: Optional[RequestContext] = None, **kwargs):
        """Log debug message with context."""
        self._log("DEBUG", message, ctx, **kwargs)

    def info(self, message: str, ctx: Optional[RequestContext] = None, **kwargs):
        """Log info message with context."""
        self._log("INFO", message, ctx, **kwargs)

    def warning(self, message: str, ctx: Optional[RequestContext] = None, **kwargs):
        """Log warning message with context."""
        self._log("WARNING", message, ctx, **kwargs)

    def error(self, message: str, ctx: Optional[RequestContext] = None, **kwargs):
        """Log error message with context."""
        self._log("ERROR", message, ctx, **kwargs)

    def critical(self, message: str, ctx: Optional[RequestContext] = None, **kwargs):
        """Log critical message with context."""
        self._log("CRITICAL", message, ctx, **kwargs)


def get_logger(service_name: str) -> StructuredLogger:
    """Get a structured logger for the given service."""
    return StructuredLogger(service_name)

