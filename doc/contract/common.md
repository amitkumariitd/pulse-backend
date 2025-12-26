# Common Contracts

This document defines shared schemas, headers, enums, and error formats
used across GAPI and Order Service.

No endpoints are defined here.

---

## Common Headers

### Request Headers

#### Required (GAPI)
- `Content-Type: application/json`
- `Idempotency-Key: <uuid>`
  Required for order creation to ensure idempotent processing.

#### Optional (Tracing)
- Every request MUST have a `request_id`, `trace_source`
- Generated if not provided via `X-Request-Id`, `X-Trace-Id` 
- Every request MUST have a `request_source`, `trace_source`


## Error Format

All errors MUST follow this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "request_id": "uuid",
    "trace_id": "uuid",
    "details": {}
  }
}
```

