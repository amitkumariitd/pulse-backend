# Common Contracts

This document defines shared schemas, headers, enums, and error formats
used across GAPI and Order Service.

No endpoints are defined here.

---

## Common Headers

### Required (GAPI)
- `Content-Type: application/json`
- `Idempotency-Key: <uuid>`

### Optional
- `X-Request-Id: <uuid>`  
  If not provided, the system will generate one.

---