import json
import logging
from typing import Any, Dict

from shared.observability.logger import get_logger, FORBIDDEN_KEYS
from shared.observability.context import RequestContext


class DummyHandler(logging.Handler):
    """Capture log records for assertions."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:  # pragma: no cover - trivial
        self.records.append(record)


def _make_logger(service_name: str = "test-service") -> tuple[Any, DummyHandler]:
    """Create a logger instance with a dummy handler attached."""
    logger = get_logger(service_name)

    # Remove any existing handlers and attach dummy
    logger.logger.handlers = []
    handler = DummyHandler()
    logger.logger.addHandler(handler)

    return logger, handler


def test_logger_wraps_kwargs_in_data_envelope():
    logger, handler = _make_logger()

    logger.info("Test message", extra_field="value", count=1)

    assert len(handler.records) == 1
    payload = json.loads(handler.records[0].getMessage())

    assert payload["message"] == "Test message"
    assert "data" in payload
    assert payload["data"] == {"extra_field": "value", "count": 1}


def test_logger_merges_explicit_data_and_kwargs():
    logger, handler = _make_logger()

    logger.info("With data", data={"a": 1}, b=2)

    payload = json.loads(handler.records[0].getMessage())
    assert payload["data"] == {"a": 1, "b": 2}


def test_logger_keeps_non_dict_data_under_value_key():
    logger, handler = _make_logger()

    logger.info("Non-dict data", data=[1, 2, 3])

    payload = json.loads(handler.records[0].getMessage())
    assert payload["data"] == {"value": [1, 2, 3]}


def test_logger_includes_context_fields_top_level():
    logger, handler = _make_logger()

    ctx = RequestContext(
        trace_id="t123",
        trace_source="SRC",
        request_id="r456",
        request_source="REQ",
        span_id="s789abcd",
        span_source="SPAN",
    )

    logger.info("With context", ctx, data={"x": 1})

    payload = json.loads(handler.records[0].getMessage())

    # Context fields are top-level
    assert payload["trace_id"] == "t123"
    assert payload["request_id"] == "r456"
    assert payload["span_id"] == "s789abcd"
    assert payload["data"] == {"x": 1}


def test_logger_allows_structured_top_level_overrides():
    logger, handler = _make_logger()

    ctx = RequestContext(
        trace_id="t-ctx",
        trace_source="SRC",
        request_id="r-ctx",
        request_source="REQ",
        span_id="sctxabcd",
        span_source="SPAN",
    )

    logger.info("Override", ctx, trace_id="t-override", order_id="ord_1")

    payload = json.loads(handler.records[0].getMessage())
    assert payload["trace_id"] == "t-override"
    assert payload["order_id"] == "ord_1"


def test_logger_filters_forbidden_top_level_keys():
    logger, handler = _make_logger()

    kwargs: Dict[str, Any] = {key: "SECRET" for key in FORBIDDEN_KEYS}
    kwargs["safe"] = "ok"

    logger.info("Secrets", **kwargs)

    payload = json.loads(handler.records[0].getMessage())

    # No forbidden key should appear anywhere at top level or inside data
    for forbidden in FORBIDDEN_KEYS:
        assert forbidden not in payload
        if "data" in payload and isinstance(payload["data"], dict):
            assert forbidden not in payload["data"]

    assert payload["data"] == {"safe": "ok"}

