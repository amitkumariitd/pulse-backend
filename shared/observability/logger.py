import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Optional, Dict

from .context import RequestContext


# Security: Keys that should never be logged (top-level fields)
FORBIDDEN_KEYS = {
	"authorization",
	"token",
	"password",
	"secret",
	"api_key",
	"bearer",
	"jwt",
	"credential",
	"auth",
}

# Fields that are allowed as top-level structured keys rather than inside `data`
STRUCTURED_KEYS = {
	"trace_id",
	"trace_source",
	"request_id",
	"request_source",
	"order_id",
	"span_source",
}


class StructuredLogger:
	"""Structured JSON logger that accepts RequestContext explicitly.

	Usage:
	    logger = get_logger("pulse.workers.splitting")
	    logger.info("Order created", ctx, data={"instrument": "NSE:RELIANCE"})
	"""

	def __init__(self, logger_name: str):
		self.logger_name = logger_name
		self.logger = logging.getLogger(logger_name)
		self.logger.setLevel(logging.DEBUG)

		handler = logging.StreamHandler(sys.stdout)
		handler.setFormatter(logging.Formatter('%(message)s'))
		self.logger.addHandler(handler)
		self.logger.propagate = False

	def _sanitize_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
		"""Remove forbidden *top-level* keys for security.

		NOTE: This intentionally only filters the first level of kwargs.
		Nested dictionaries (e.g. inside ``data={...}``) are not yet
		inspected.

		TODO: Consider deep-sanitising nested dicts (especially inside the
		``data`` payload) to remove forbidden keys like Authorization
		headers, while keeping performance overhead reasonable.
		"""
		return {k: v for k, v in kwargs.items() if k.lower() not in FORBIDDEN_KEYS}

	def _log(self, level: str, message: str, ctx: Optional[RequestContext] = None, **kwargs):
		"""Internal log method.

		Priority (later overrides earlier):
		1. Base fields (timestamp, level, service, message)
		2. Context fields (if ctx provided)
		3. Structured top-level overrides (trace_id, order_id, ...)
		4. Arbitrary user-provided kwargs nested under ``data``
		"""
		# Base log entry
		log_entry: Dict[str, Any] = {
			"timestamp": datetime.now(timezone.utc)
			.isoformat()
			.replace("+00:00", "Z"),
			"level": level,
			"logger": self.logger_name,
			"message": message,
		}

		# Include context if provided (trace_id, request_id, span_source, ...)
		if ctx:
			log_entry.update(ctx.to_dict())

		# Sanitize user-provided kwargs first
		safe_kwargs = self._sanitize_kwargs(kwargs)

		# 1) Allow known structured fields to override context values at the top level
		#    (e.g. trace_id, order_id).
		for key in list(STRUCTURED_KEYS):
			if key in safe_kwargs:
				log_entry[key] = safe_kwargs.pop(key)

		# 2) Everything else goes under the standard `data` envelope.
		data_payload: Dict[str, Any] = {}

		if "data" in safe_kwargs:
			data_value = safe_kwargs.pop("data")
			if isinstance(data_value, dict):
				data_payload.update(data_value)
			elif data_value is not None:
				# Keep non-dict payloads under a generic key to honour the
				# contract that `data` is a JSON object.
				data_payload["value"] = data_value

		# Any remaining kwargs are arbitrary and should live inside `data`.
		if safe_kwargs:
			data_payload.update(safe_kwargs)

		if data_payload:
			log_entry["data"] = data_payload

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


def get_logger(logger_name: str) -> StructuredLogger:
    """Get a structured logger with the given name."""
    return StructuredLogger(logger_name)

