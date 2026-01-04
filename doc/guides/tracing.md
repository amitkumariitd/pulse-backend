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
| span_source | Service call path (for logging only, not stored in DB) |

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
trace_source = GAPI:POST/api/orders
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

### span_source
- `span_source` shows the service call path
- Built by appending current service to parent's `request_source`
- Used for logging only, NOT stored in database

**Example:**
```
# Service A (GAPI)
span_source = GAPI:POST/api/orders

# Service B (PULSE) - receives call from GAPI
span_source = GAPI:POST/api/orders->PULSE:POST/internal/orders
```

**Breakdown:**
- `s` = prefix (identifies this as a span ID)
- `a1b2c3d4` = 8 random hexadecimal characters (for uniqueness)

**Benefits:**
- Compact format (9 characters)
- Globally unique (4.3 billion combinations)
- Tracks individual operations within a request
- Shows service call hierarchy via parent_span_id
- Enables distributed tracing across service boundaries

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
request_source = GAPI:POST/api/orders
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

## Source Format

### trace_source and request_source

Both follow the format: `SERVICE_NAME:METHOD/path`

**Examples:**
```
GAPI:GET/health
GAPI:POST/api/orders
GAPI:GET/api/orders/123
ORDER_SERVICE:POST/internal/orders
ORDER_SERVICE:GET/health
```

**Rules:**
- Service name is UPPERCASE
- HTTP method is UPPERCASE (GET, POST, PUT, DELETE, etc.)
- No space between method and path
- Path starts with `/`
- Path parameters are included (e.g., `/api/orders/123`)

**Why include HTTP method?**
- Distinguishes between different operations on the same path
  - `GET/api/orders` (list orders) vs `POST/api/orders` (create order)
- Makes traces more specific and searchable
- Aligns with standard HTTP semantics

**Why paths instead of operation names?**
- Paths are automatically available in middleware
- Paths are standard REST identifiers
- Paths appear in logs, metrics, and traces consistently
- No need to manually maintain operation_id on every endpoint

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

### Generating span_id

```python
import secrets

def generate_span_id() -> str:
    random_hex = secrets.token_hex(4)  # 4 bytes = 8 hex chars
    return f"s{random_hex}"

# Example: sa1b2c3d4
```

### Validation

IDs must match the pattern:
- `trace_id`: `^t\d{10}[0-9a-f]{12}$`
- `request_id`: `^r\d{10}[0-9a-f]{12}$`
- `span_id`: `^s[0-9a-f]{8}$`

**Valid:**
- `t1735228800a1b2c3d4e5f6` ✅
- `r1735228800f6e5d4c3b2a1` ✅
- `sa1b2c3d4` ✅

**Invalid:**
- `t-1735228800-abc` ❌ (wrong format)
- `r1735228800` ❌ (missing random hex)
- `t1735228800ABC` ❌ (uppercase hex not allowed)
- `trace-123` ❌ (wrong format)
- `s123` ❌ (span_id must be 8 hex chars)
- `sABCD1234` ❌ (uppercase hex not allowed)

---

## Request Flow (Simplified)

### Ingress (Middleware)
- Continue trace if present, else create new `trace_id`
- Generate `request_id` if missing
- Generate new `span_id` for this operation
- Set all corresponding sources

---

### Synchronous Service Calls (HTTP)

**Sender (HTTP Client):**
- Propagates via headers:
  - `X-Trace-Id` + `X-Trace-Source`
  - `X-Request-Id` + `X-Request-Source`
  - `X-Span-Id` (current span_id) + `X-Span-Source`
- Does NOT generate new span_id (receiver will do this)

**Receiver (Middleware):**
- Extracts incoming `X-Span-Id` as `parent_span_id`
- Generates NEW `span_id` for its own operation
- Builds `span_source` by appending to parent's `X-Span-Source`
- Logs both `span_id` (new) and `parent_span_id` (from sender)

**Example:**
```
# GAPI sends to PULSE
Headers sent by GAPI:
  X-Span-Id: sa1b2c3d4
  X-Span-Source: GAPI:POST/api/orders

# PULSE receives and creates context
PULSE context:
  span_id: sb2c3d4e5  (NEW, generated by PULSE)
  parent_span_id: sa1b2c3d4  (from X-Span-Id header)
  span_source: GAPI:POST/api/orders->PULSE:POST/internal/orders
```

---

### Asynchronous Processing (Messaging System)
- Propagate in message:
  - `trace_id` + `trace_source`
  - `request_id` + `request_source`
  - `span_id` + `span_source`

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