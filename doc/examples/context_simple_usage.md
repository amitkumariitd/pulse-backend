# Request Context - Simple Usage Guide

## What is RequestContext?

A simple, immutable object containing tracing information:

```python
@dataclass(frozen=True)
class RequestContext:
    trace_id: str         # e.g., "t-8fa21c9d"
    trace_source: str     # e.g., "GAPI:/api/orders"
    request_id: str       # e.g., "r-912873"
    request_source: str   # e.g., "ORDER_SERVICE:/internal/orders"
```

**Purpose:** Track requests across services for observability.

---

## Example 1: Basic Flow

### Step 1: Middleware Creates Context

```python
from fastapi import Request
from shared.observability.context import RequestContext

async def context_middleware(request: Request, call_next):
    # Create context from headers (or generate IDs)
    ctx = RequestContext(
        trace_id=request.headers.get('X-Trace-Id') or generate_id('t'),
        trace_source=request.headers.get('X-Trace-Source') or "GAPI:/api/orders",
        request_id=request.headers.get('X-Request-Id') or generate_id('r'),
        request_source="GAPI:/api/orders"
    )
    
    # Attach to request
    request.state.context = ctx
    
    response = await call_next(request)
    return response
```

### Step 2: Endpoint Receives Context

```python
from fastapi import Depends
from shared.observability.logger import get_logger

logger = get_logger("gapi")

def get_context(request: Request) -> RequestContext:
    return request.state.context

@app.post("/api/orders")
async def create_order(
    order_data: dict,
    ctx: RequestContext = Depends(get_context)
):
    # Log with context
    logger.info("Order creation requested", ctx)
    
    # Pass to business logic
    result = await process_order(order_data, ctx)
    
    return {"order_id": result.id}
```

### Step 3: Business Logic Receives Context

```python
async def process_order(order_data: dict, ctx: RequestContext):
    logger.info("Processing order", ctx)
    
    # Validate
    validate_order(order_data)
    
    # Save (pass context to repository)
    order = await save_order(order_data, ctx)
    
    logger.info("Order saved", ctx)
    return order
```

### Step 4: Repository Receives Context

```python
async def save_order(order_data: dict, ctx: RequestContext):
    # Include tracing in database
    await db.execute(
        """
        INSERT INTO orders (id, instrument, trace_id, request_id)
        VALUES ($1, $2, $3, $4)
        """,
        order_data['id'],
        order_data['instrument'],
        ctx.trace_id,
        ctx.request_id
    )
    
    logger.info("Order persisted to database", ctx)
    return Order(**order_data)
```

---

## Example 2: Service-to-Service Calls

### GAPI Calls Order Service

```python
from shared.http.client import ContextPropagatingClient

async def forward_order(order_data: dict, ctx: RequestContext):
    logger.info("Forwarding to Order Service", ctx)
    
    # Client automatically adds context headers
    client = ContextPropagatingClient("http://localhost:8001")
    response = await client.post(
        "/internal/orders",
        json=order_data,
        context=ctx
    )
    
    return response.json()
```

**Headers Automatically Added:**
- `X-Trace-Id: t-8fa21c9d`
- `X-Trace-Source: GAPI:/api/orders`
- `X-Request-Id: r-912873`
- `X-Request-Source: GAPI:/api/orders`

### Order Service Receives Context

```python
# Middleware extracts headers and creates context
@app.post("/internal/orders")
async def create_order_internal(
    order_data: dict,
    ctx: RequestContext = Depends(get_context)
):
    # Context includes trace_id and request_id from GAPI
    logger.info("Order received from GAPI", ctx)
    
    # Process order
    order = await process_order(order_data, ctx)
    
    return {"order_id": order.id}
```

---

## Example 3: Logging with Context

```python
from shared.observability.logger import get_logger

logger = get_logger("pulse")

async def process_order(order_data: dict, ctx: RequestContext):
    # Pass context to logger - ALL tracing fields are automatically included
    logger.info("Starting order processing", ctx)

    # Log output will include:
    # - trace_id, trace_source
    # - request_id, request_source
    # - span_source
    # All extracted automatically from ctx!

    # ... business logic ...

    logger.info("Order processing complete", ctx, data={"status": "success"})
```

**What gets logged:**
```json
{
  "timestamp": "2025-12-25T10:30:45.123Z",
  "level": "INFO",
  "logger": "pulse",
  "trace_id": "t1234567890abcdef1234",
  "trace_source": "GAPI:POST/api/orders",
  "request_id": "r1234567890abcdef1234",
  "request_source": "PULSE:POST/internal/orders",
  "span_source": "GAPI:POST/api/orders->PULSE:POST/internal/orders",
  "message": "Starting order processing"
}
```

See `contracts/guides/logging.md` for log format details.

---

## Key Patterns

### 1. Creation
Middleware creates context from HTTP headers

### 2. Passing
Explicit parameter in all functions:
```python
async def my_function(data: dict, ctx: RequestContext):
    pass
```

### 3. Logging
Always pass context to logger:
```python
logger.info("Message", ctx)
```

### 4. HTTP Propagation
Use `ContextPropagatingClient` for service-to-service calls

### 5. Immutability
Context never changes - same object flows through entire request

---

## Summary

✅ **Simple** - Just 4 fields for tracing
✅ **Explicit** - Passed as function parameter
✅ **Immutable** - Cannot be modified
✅ **Typed** - IDE autocomplete works
✅ **Focused** - Only observability, nothing else

**Not Included:**
- ❌ User ID, client ID → Handle in auth layer
- ❌ Order ID, account ID → Pass as function parameters
- ❌ Metadata → Pass as function parameters

**Keep it simple!**

