# Distributed Tracing Standard

## Purpose

Distributed tracing allows us to follow a single request across:

- API Gateway
- Internal synchronous service calls
- Asynchronous systems (Kafka)
- Databases

This document explains the tracing model.  
Mandatory enforcement lives in `RULES.md`.

---

## Core Principles

- Tracing is end-to-end
- Implemented via middleware, not business logic
- IDs and their sources always travel together

---

## Core Identifiers

| Identifier | Description                                    |
|----------|------------------------------------------------|
| trace_id | Global trace identifier (starts with `t`)      |
| trace_source | Origin of the trace                            |
| request_id | Synchronous request identifier (starts with `r`) |
| request_source | Origin of the request                          |

---

## Identifier Semantics

### trace_id & trace_source
- `trace_id` starts with `t`
- One per end-to-end request
- Shared across sync and async flows
- `trace_source` defines where the trace started

**Format:** `t` + Unix timestamp (seconds) + 12 hexadecimal characters

**Example:**
```
trace_id = t1735228800a1b2c3d4e5f6
trace_source = GAPI:create_order
```

**Breakdown:**
- `t` = prefix (identifies this as a trace ID)
- `1735228800` = Unix timestamp in seconds (Dec 26, 2024 16:00:00 UTC)
- `a1b2c3d4e5f6` = 12 random hexadecimal characters (for uniqueness)

**Benefits:**
- Sortable by time (timestamp first)
- Globally unique (281 trillion combinations per second)
- Easy to extract timestamp for debugging
- Shorter than UUID (23 characters vs 36)

---

### request_id & request_source
- `request_id` starts with `r`
- Generated at ingress if missing
- Propagated across **all synchronous service calls**
- `request_source` identifies the service and endpoint that accepted the request

**Format:** `r` + Unix timestamp (seconds) + 12 hexadecimal characters

**Example:**
```
request_id = r1735228800f6e5d4c3b2a1
request_source = GAPI:create_order
```

**Breakdown:**
- `r` = prefix (identifies this as a request ID)
- `1735228800` = Unix timestamp in seconds (Dec 26, 2024 16:00:00 UTC)
- `f6e5d4c3b2a1` = 12 random hexadecimal characters (for uniqueness)

**Benefits:**
- Same format as trace_id for consistency
- Sortable by time
- Globally unique
- Easy to correlate with trace_id by timestamp

---

## ID Generation

### Generating trace_id

```python
import time
import secrets

def generate_trace_id() -> str:
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)  # 6 bytes = 12 hex chars
    return f"t{timestamp}{random_hex}"

# Example: t1735228800a1b2c3d4e5f6
```

### Generating request_id

```python
import time
import secrets

def generate_request_id() -> str:
    timestamp = int(time.time())
    random_hex = secrets.token_hex(6)  # 6 bytes = 12 hex chars
    return f"r{timestamp}{random_hex}"

# Example: r1735228800f6e5d4c3b2a1
```

### Validation

IDs must match the pattern:
- `trace_id`: `^t\d{10}[0-9a-f]{12}$`
- `request_id`: `^r\d{10}[0-9a-f]{12}$`

**Valid:**
- `t1735228800a1b2c3d4e5f6` ✅
- `r1735228800f6e5d4c3b2a1` ✅

**Invalid:**
- `t-1735228800-abc` ❌ (wrong format)
- `r1735228800` ❌ (missing random hex)
- `t1735228800ABC` ❌ (uppercase hex not allowed)
- `trace-123` ❌ (wrong format)

---

## Request Flow (Simplified)

### Ingress
- Continue trace if present, else create new `trace_id`
- Generate `request_id` if missing
- Set all corresponding sources

---

### Synchronous Service Calls
- Propagate:
  - `trace_id` + `trace_source`
  - `request_id` + `request_source`

---

### Asynchronous Processing (Messaging System)
- Propagate:
  - `trace_id` + `trace_source`
  - `request_id` + `request_source`

---

## All Writes

All writes must automatically include tracing information.
This enables Storage → trace → log correlation.

---

## Logging

All logs should include tracing info.


## Technology Standard

- OpenTelemetry
- W3C Trace Context (`traceparent`)

---

## Relationship to RULES.md

- `RULES.md` defines mandatory requirements
- This document explains intent and usage

If there is a conflict, `RULES.md` always takes precedence.