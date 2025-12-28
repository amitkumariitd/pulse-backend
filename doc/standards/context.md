# Request Context Standard

## Purpose

Request context is the collection of metadata that flows with every request across:
- HTTP boundaries (client → GAPI → Order Service)
- Function boundaries (middleware → handlers → domain logic)
- Storage boundaries (application → database)
- Logging boundaries (code → structured logs)

This document defines what context is, how it's structured, and how it propagates.

---

## Core Principles

1. **Context is an object** - Explicit `RequestContext` object passed through the application
2. **Context is immutable** - Use `with_*` methods to create enriched copies
3. **Context is typed** - Clear separation: Tracing, Identity, Domain
4. **Context is passed explicitly** - Function parameters receive context
5. **Context propagates via parameters** - No global state or magic

---

## Context Structure

Request context is a simple, immutable dataclass:

```python
@dataclass(frozen=True)
class RequestContext:
    trace_id: str                    # Global trace ID (e.g., "t1735228800a1b2c3d4e5f6")
    trace_source: str                # Where trace started (e.g., "GAPI:POST/api/orders")
    request_id: str                  # Request ID (e.g., "r1735228800f6e5d4c3b2a1")
    request_source: str              # Current service (e.g., "PULSE:POST/internal/orders")
    span_id: str                     # Span ID for this operation (e.g., "sa1b2c3d4")
    span_source: str                 # Service call path (e.g., "GAPI:POST/api/orders->PULSE:POST/internal/orders")
    parent_span_id: Optional[str]    # Parent span ID (e.g., "sa1b2c3d4") - for span hierarchy
```

### Field Descriptions

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `trace_id` | string | Global trace identifier for end-to-end tracing | `t1735228800a1b2c3d4e5f6` |
| `trace_source` | string | Service and endpoint where trace originated | `GAPI:POST/api/orders` |
| `request_id` | string | Unique identifier for this request | `r1735228800f6e5d4c3b2a1` |
| `request_source` | string | Current service and endpoint processing the request | `PULSE:POST/internal/orders` |
| `span_id` | string | Identifier for this specific operation (always generated fresh) | `sa1b2c3d4` |
| `span_source` | string | Service call path showing caller and target | `GAPI:POST/api/orders->PULSE:POST/internal/orders` |
| `parent_span_id` | string (optional) | Span ID of the calling service (from X-Span-Id header) | `sa1b2c3d4` |

### Design Principles

**Simple and Focused:**
- Only tracing/observability fields
- No identity (user_id, client_id) - handle separately in auth layer
- No domain data (order_id, account_id) - pass as function parameters
- Immutable - cannot be modified after creation

**Rationale:**
- Context is for **cross-cutting observability** only
- Identity belongs in authentication/authorization layer
- Domain data belongs in function parameters
- Keeps concerns separated and explicit

---

## Context Lifecycle

### 1. Creation (Middleware)
```python
# Middleware extracts headers and creates context
# Incoming X-Span-Id is treated as parent_span_id
parent_span_id = headers.get('X-Span-Id')  # From calling service
parent_span_source = headers.get('X-Span-Source')

# Build span_source by appending to parent's span_source
if parent_span_source:
    span_source = f"{parent_span_source}->GAPI:POST/api/orders"
else:
    span_source = "GAPI:POST/api/orders"

ctx = RequestContext(
    trace_id=headers.get('X-Trace-Id') or generate_trace_id(),
    trace_source=headers.get('X-Trace-Source') or f"GAPI:POST/api/orders",
    request_id=headers.get('X-Request-Id') or generate_request_id(),
    request_source="GAPI:POST/api/orders",
    span_id=generate_span_id(),  # Always generate NEW span_id
    span_source=span_source,
    parent_span_id=parent_span_id  # From X-Span-Id header
)

# Attach to request state
request.state.context = ctx

# Pass to handler
response = await handler(request)
```

### 2. Propagation (Explicit Passing)
```python
# Endpoint receives context via dependency
@app.post("/api/orders")
async def create_order(
    order_data: dict,
    ctx: RequestContext = Depends(get_context)
):
    logger.info("Order received", ctx)

    # Pass to business logic
    result = await process_order(order_data, ctx)
    return result

# Business logic receives context
async def process_order(order_data: dict, ctx: RequestContext):
    logger.info("Processing order", ctx)

    # Pass to repository
    order = await save_order(order_data, ctx)

    logger.info("Order processed", ctx)
    return order
```

### 3. Cross-Service (HTTP Headers)
```python
# GAPI calls Pulse Service
async def forward_to_pulse_service(order_data: dict, ctx: RequestContext):
    client = ContextPropagatingClient("http://localhost:8001")

    # Client extracts context and adds headers
    # Headers: X-Trace-Id, X-Request-Id, X-Span-Id, X-Span-Source, etc.
    response = await client.post(
        "/internal/orders",
        json=order_data,
        context=ctx
    )

    return response.json()

# Pulse Service middleware recreates context from headers
# Incoming X-Span-Id becomes parent_span_id
# Generates NEW span_id for this service's operation
parent_span_id = headers.get('X-Span-Id')  # GAPI's span_id
parent_span_source = headers.get('X-Span-Source')

# Build span_source by appending to parent
if parent_span_source:
    span_source = f"{parent_span_source}->PULSE:POST/internal/orders"
else:
    span_source = "PULSE:POST/internal/orders"

ctx = RequestContext(
    trace_id=headers.get('X-Trace-Id'),
    trace_source=headers.get('X-Trace-Source'),
    request_id=headers.get('X-Request-Id'),
    request_source="PULSE:POST/internal/orders",
    span_id=generate_span_id(),  # NEW span for this service
    span_source=span_source,
    parent_span_id=parent_span_id  # GAPI's span_id
)
```

---

## Propagation Rules

### Rule 1: HTTP Headers
When making HTTP calls, propagate context via headers:

| Context Field | HTTP Header |
|--------------|-------------|
| `trace_id` | `X-Trace-Id` |
| `trace_source` | `X-Trace-Source` |
| `request_id` | `X-Request-Id` |
| `request_source` | `X-Request-Source` |
| `span_id` | `X-Span-Id` |
| `span_source` | `X-Span-Source` |

### Rule 2: Function Parameters
Context MUST be passed as an explicit parameter:

```python
# Good
async def process_order(order_data: dict, ctx: RequestContext):
    pass

# Bad - no context parameter
async def process_order(order_data: dict):
    pass
```

### Rule 3: Logging
All logs MUST include context:

```python
logger.info("Order created", ctx)
```

### Rule 4: Database Writes
All database writes MUST include context for tracing and audit trail.

Pass `RequestContext` to repository methods - repositories handle extracting tracing fields.

```python
# Repository receives context and extracts tracing fields
async def save_order(order_data: dict, ctx: RequestContext):
    repo = OrderRepository(db_pool)
    order = await repo.create_order(order_data, ctx)
    return order
```

**Schema requirements**: See [PostgreSQL Standard](postgres.md) for required tracing columns.

### Rule 5: Async Tasks
When queuing async tasks, include context in message payload:

```python
await queue.publish({
    "order_id": order.id,
    "trace_id": ctx.trace_id,
    "trace_source": ctx.trace_source,
    "request_id": ctx.request_id,
    "span_id": ctx.span_id,
    "span_source": ctx.span_source
})
```

---

## Context Immutability

Context is **immutable** - it cannot be changed after creation.

**Why Immutable?**
- Prevents accidental modifications
- Makes data flow explicit and traceable
- Simplifies reasoning about code
- Thread-safe by design

**Example:**
```python
# Context created at ingress
ctx = RequestContext(
    trace_id="t1735228800a1b2c3d4e5f6",
    trace_source="GAPI:POST/api/orders",
    request_id="r1735228800f6e5d4c3b2a1",
    request_source="GAPI:POST/api/orders",
    span_id="sa1b2c3d4",
    span_source="GAPI:POST/api/orders"
)

# Cannot modify
ctx.trace_id = "t-new"  # Error: frozen dataclass

# Context flows unchanged through entire request
```

---

## Security Rules

**Context contains only tracing IDs:**
- ✅ `trace_id`, `request_id`, `span_id` - Safe to log
- ✅ `trace_source`, `request_source`, `span_source` - Safe to log

**NEVER include in context:**
- ❌ Passwords or credentials
- ❌ JWT tokens or API keys
- ❌ Authorization headers
- ❌ User IDs or client IDs (handle in auth layer)
- ❌ Business data (order_id, account_id - pass as parameters)
- ❌ Sensitive PII

**Rationale:**
- Context is logged everywhere
- Only include what's safe to log
- Keep context minimal and focused

---

## Implementation Requirements

### 1. Context Storage
Use Python `contextvars.ContextVar` for async-safe storage.

### 2. Middleware
- Extract headers at ingress
- Set context before handler
- Clear context after response

### 3. Logger
- Auto-inject context into all log entries
- Filter forbidden keys

### 4. HTTP Client
- Auto-add context headers to outgoing requests

### 5. Dependencies
- Provide FastAPI dependency for explicit access

---

## See Also

- [Tracing Standard](tracing.md) - Detailed tracing semantics
- [Logging Standard](logging.md) - Log format and requirements
- [Testing Standard](testing.md) - Testing context propagation

