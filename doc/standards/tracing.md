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

Example:
trace_id = t8fa21c9d
trace_source = GAPI:create_order

---

### request_id & request_source
- `request_id` starts with `r`
- Generated at ingress if missing
- Propagated across **all synchronous service calls**
- `request_source` identifies the service and endpoint that accepted the request

Example:
request_id = r-912873
request_source = GAPI:create_order

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