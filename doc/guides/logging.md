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
  "service": "gapi",
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
| `service` | string | Service name: `gapi` or `order_service` |
| `message` | string | Human-readable log message |

---

## Tracing Fields

Include when available:

| Field | Type | Description |
|-------|------|-------------|
| `trace_id` | string | Global trace identifier (starts with `t-`) |
| `trace_source` | string | Origin of the trace (format: `SERVICE:endpoint`) |
| `request_id` | string | Request identifier (starts with `r-`) |
| `request_source` | string | Origin of the request (format: `SERVICE:endpoint`) |
| `order_id` | string | Order identifier (starts with `o-`), include when applicable |

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
  "service": "gapi",
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
  "service": "order_service",
  "trace_id": "t-8fa21c9d",
  "trace_source": "GAPI:create_order",
  "request_id": "r-445566",
  "request_source": "ORDER:create_order",
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

---

## Relationship to Other Standards

- Tracing identifiers defined in `doc/guides/tracing.md`
- Security rules enforced in `.augment/rules/rules.md`

