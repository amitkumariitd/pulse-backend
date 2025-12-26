#!/usr/bin/env python3
"""Test script to demonstrate structured logging"""

from shared.observability.logger import get_logger
from shared.observability.context import set_trace_context

logger = get_logger("gapi")

print("=== Example 1: Basic log ===")
logger.info("Service started")

print("\n=== Example 2: Log with tracing context ===")
set_trace_context(
    trace_id="t-8fa21c9d",
    trace_source="GAPI:create_order",
    request_id="r-912873",
    request_source="GAPI:create_order"
)
logger.info(
    "Received order creation request",
    trace_id="t-8fa21c9d",
    trace_source="GAPI:create_order",
    request_id="r-912873",
    request_source="GAPI:create_order",
    data={"instrument": "NSE:RELIANCE", "action": "BUY"}
)

print("\n=== Example 3: Error log with order_id ===")
logger.error(
    "Failed to persist order",
    trace_id="t-8fa21c9d",
    trace_source="GAPI:create_order",
    request_id="r-445566",
    request_source="ORDER:create_order",
    order_id="o-abc123",
    data={
        "error_code": "DATABASE_ERROR",
        "error_message": "Connection timeout",
        "retry_attempt": 2
    }
)

print("\n=== Example 4: Order state transition ===")
logger.info(
    "Order state transition",
    trace_id="t-8fa21c9d",
    trace_source="GAPI:create_order",
    request_id="r-445566",
    request_source="ORDER:create_order",
    order_id="o-abc123",
    data={"from_state": "PENDING", "to_state": "ACCEPTED"}
)

print("\n=== Example 5: Different log levels ===")
logger.debug("Debug message", data={"detail": "verbose info"})
logger.warning("Warning message", data={"reason": "unexpected condition"})
logger.critical("Critical message", data={"impact": "service unavailable"})

