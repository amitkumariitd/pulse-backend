# Logging Standard

## Purpose

All services must emit structured JSON logs with consistent format and required fields.

---

## Log Format

All logs MUST be valid JSON with the following structure:

```json
{
  "timestamp": "2025-12-25T10:30:45.123Z",
  "level": "INFO",
  "logger": "gapi",
  "trace_id": "t-8fa21c9d",
  "trace_source": "GAPI:create_order",
  "request_id": "r-912873",
  "request_source": "GAPI:create_order",
  "message": "Order created successfully",
  "data": {
    "instrument": "NSE:RELIANCE",
    "quantity": 10
  }
}
```

---

## Required Fields

Every log entry MUST include:

| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | string | ISO 8601 format with milliseconds (UTC) |
| `level` | string | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `logger` | string | Logger name: `gapi`, `pulse`, `pulse.workers.splitting`, etc. |
| `message` | string | Human-readable log message |

---

## Tracing Fields

Include when available (automatically added when `RequestContext` is passed to logger):

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | Global trace identifier (starts with `t-`) |
| `trace_source` | string | Origin of the trace (format: `SERVICE:endpoint`) |
| `request_id` | string | Request identifier (starts with `r-`) |
| `request_source` | string | Current service and endpoint (format: `SERVICE:endpoint`) |
| `span_source` | string | Service call path (e.g., `GAPI:POST/api/orders->PULSE:POST/internal/orders`) |
| `order_id` | string | Order identifier (starts with `o-`), include when applicable |

**Note:** When you pass `RequestContext` to the logger, all these fields are automatically included in the log output.

---

## Data Field

The `data` field is optional and contains structured context:

- MUST be a JSON object (not string, array, or primitive)
- Use for domain-specific information
- Keep it flat when possible
- Do NOT include sensitive information

**Examples:**

```json
{
  "message": "Order validation failed",
  "data": {
    "validation_errors": ["invalid_quantity", "missing_instrument"],
    "submitted_quantity": -5
  }
}
```

```json
{
  "message": "HTTP request to Order Service",
  "data": {
    "method": "POST",
    "url": "/internal/orders",
    "status_code": 201,
    "duration_ms": 45
  }
}
```

## Security Rules

**NEVER log:**
- Passwords or credentials
- API keys or tokens
- Authorization headers (e.g., `Bearer ...`)
- Secrets or encryption keys
- Full credit card numbers or sensitive PII

**Safe to log:**
- Request IDs and trace IDs
- Order IDs and instrument symbols
- HTTP status codes and methods
- Validation error codes
- Timestamps and durations

---

## Examples

### Successful Request
```json
{
  "timestamp": "2025-12-25T10:30:45.123Z",
  "level": "INFO",
  "logger": "gapi",
  "trace_id": "t-8fa21c9d",
  "trace_source": "GAPI:create_order",
  "request_id": "r-912873",
  "request_source": "GAPI:create_order",
  "message": "Received order creation request",
  "data": {
    "instrument": "NSE:RELIANCE",
    "action": "BUY"
  }
}
```

### Error with Context
```json
{
  "timestamp": "2025-12-25T10:30:46.789Z",
  "level": "ERROR",
  "logger": "pulse",
  "trace_id": "t-8fa21c9d",
  "trace_source": "GAPI:create_order",
  "request_id": "r-445566",
  "request_source": "PULSE:create_order",
  "message": "Failed to persist order",
  "data": {
    "error_code": "DATABASE_ERROR",
    "error_message": "Connection timeout",
    "retry_attempt": 2
  }
}
```


## Implementation Notes

- Use structured logging library (e.g., `structlog`, `python-json-logger`)
- Configure via middleware, not in business logic
- Tracing fields should be injected automatically from context
- All timestamps in UTC
- One log entry per line (newline-delimited JSON)

### How to Use the Logger

```python
from shared.observability.logger import get_logger
from shared.observability.context import RequestContext

logger = get_logger("pulse.workers.splitting")

async def process_order(order_data: dict, ctx: RequestContext):
    # Pass ctx to logger - all tracing fields automatically included
    logger.info("Processing order", ctx, data={"instrument": order_data["instrument"]})

    # Output will include:
    # - trace_id, trace_source (from ctx)
    # - request_id, request_source (from ctx)
    # - span_source (from ctx)
    # - Plus any additional data you provide
```

**Key Points:**
- Always pass `RequestContext` as the second parameter to logger methods
- All tracing fields (`trace_id`, `trace_source`, `request_id`, `request_source`, `span_source`) are automatically extracted from the context
- No need to manually add these fields to logs

---

## Relationship to Other Standards

- Tracing identifiers defined in `doc/guides/tracing.md`
- Security rules enforced in `.augment/rules/rules.md`

