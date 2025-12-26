# Request Context Object - Usage Examples

This document shows how to use the object-based `RequestContext` in Pulse Backend.

## Core Concept

Context is an **explicit, immutable object** passed through function parameters.

```python
from shared.observability.context import RequestContext, TracingContext, IdentityContext, DomainContext
```

---

## Example 1: Basic Flow

### Middleware Creates Context

```python
from fastapi import Request
from shared.observability.context import RequestContext, TracingContext, IdentityContext

async def context_middleware(request: Request, call_next):
    # Extract or generate tracing info
    ctx = RequestContext(
        tracing=TracingContext(
            trace_id=request.headers.get('X-Trace-Id') or generate_id('t'),
            trace_source=request.headers.get('X-Trace-Source') or "GAPI:/api/orders",
            request_id=request.headers.get('X-Request-Id') or generate_id('r'),
            request_source="GAPI:/api/orders"
        ),
        identity=IdentityContext(
            user_id=request.headers.get('X-User-Id'),
            client_id=request.headers.get('X-Client-Id')
        )
    )
    
    # Attach to request state
    request.state.context = ctx
    
    response = await call_next(request)
    return response
```

### Endpoint Receives Context

```python
from fastapi import Depends, Request
from shared.observability.context import RequestContext
from shared.observability.logger import get_logger

logger = get_logger("gapi")

def get_context(request: Request) -> RequestContext:
    """FastAPI dependency to extract context from request state."""
    return request.state.context

@app.post("/api/orders")
async def create_order(
    order_data: dict,
    ctx: RequestContext = Depends(get_context)
):
    # Log with context
    logger.info("Order creation requested", ctx)
    
    # Pass context to business logic
    result = await process_order(order_data, ctx)
    
    return {"order_id": result.order_id}
```

---

## Example 2: Context Enrichment

### Adding Domain Context

```python
async def process_order(order_data: dict, ctx: RequestContext) -> Order:
    logger.info("Processing order", ctx)
    
    # Create order
    order = Order.create(order_data)
    
    # Enrich context with order_id (creates new immutable copy)
    ctx = ctx.with_order_id(order.id)
    
    # All subsequent logs include order_id
    logger.info("Order validated", ctx)
    
    # Pass enriched context to repository
    await save_order(order, ctx)
    
    logger.info("Order saved", ctx)
    
    return order
```

### Multiple Enrichments

```python
async def process_order(order_data: dict, ctx: RequestContext) -> Order:
    # Add order_id
    ctx = ctx.with_order_id("ord_123")
    
    # Add account_id
    ctx = ctx.with_account_id("acc_456")
    
    # Add custom metadata
    ctx = ctx.with_metadata(
        source="webhook",
        version="v2",
        instrument="NSE:RELIANCE"
    )
    
    logger.info("Order fully enriched", ctx)
    # Log includes: trace_id, request_id, user_id, order_id, account_id, metadata
```

---

## Example 3: Identity vs Domain Separation

### Identity Context (Who)

```python
# Set during authentication
ctx = ctx.with_identity(
    user_id="user_12345",
    client_id="tradingview"
)

# Used for authorization
if ctx.identity.user_id != order.owner_id:
    raise PermissionError("Not authorized")

# Logged for audit trail
logger.info("Order accessed", ctx)
# Includes user_id for security audit
```

### Domain Context (What)

```python
# Set during business logic
ctx = ctx.with_domain(
    order_id="ord_123",
    account_id="acc_456"
)

# Used for business operations
order = await order_repo.get(ctx.domain.order_id)

# Logged for tracing
logger.info("Order retrieved", ctx)
# Includes order_id for business tracing
```

### Why Separate?

```python
# Identity: Security/Authorization concern
if not ctx.identity.user_id:
    raise Unauthorized("Authentication required")

# Domain: Business logic concern
if ctx.domain.order_id:
    order = await get_order(ctx.domain.order_id)

# Clear separation of concerns!
```

---

## Example 4: Service-to-Service Calls

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
        context=ctx  # Context passed explicitly
    )
    
    return response.json()
```

### Order Service Receives Context

```python
# Middleware extracts headers and recreates context
@app.post("/internal/orders")
async def create_order_internal(
    order_data: dict,
    ctx: RequestContext = Depends(get_context)
):
    # Context includes:
    # - tracing: from GAPI
    # - identity: from GAPI (user_id, client_id)
    # - domain: empty (will be enriched here)
    
    logger.info("Order received from GAPI", ctx)
    
    # Process and enrich
    ctx = ctx.with_order_id("ord_new_123")
    logger.info("Order created", ctx)
```

---

## Example 5: Logging with Context

### Logger Accepts Context Object

```python
from shared.observability.logger import get_logger

logger = get_logger("order_service")

async def process_order(order_data: dict, ctx: RequestContext):
    # Pass context to logger
    logger.info("Starting order processing", ctx)
    
    # Logger extracts fields from context object
    # Output includes: trace_id, request_id, user_id, etc.
    
    ctx = ctx.with_order_id("ord_123")
    logger.info("Order created", ctx)
    # Now also includes order_id
```

---

## Example 6: Repository Pattern

### Repository Receives Context

```python
class OrderRepository:
    async def save(self, order: Order, ctx: RequestContext):
        # Include tracing in database record
        await db.execute(
            """
            INSERT INTO orders (id, user_id, instrument, trace_id, request_id)
            VALUES ($1, $2, $3, $4, $5)
            """,
            order.id,
            ctx.identity.user_id,  # From identity context
            order.instrument,
            ctx.tracing.trace_id,  # From tracing context
            ctx.tracing.request_id
        )
        
        logger.info("Order persisted", ctx)
```

---

## Summary

### Key Patterns

1. **Creation**: Middleware creates `RequestContext` from headers
2. **Passing**: Explicit parameter in all functions
3. **Enrichment**: Use `with_*` methods to add domain data
4. **Separation**: Identity (who) vs Domain (what)
5. **Immutability**: Context never mutates, always creates new copies
6. **Logging**: Pass context object to logger
7. **HTTP**: Client propagates context via headers

### Benefits

✅ **Explicit** - No magic, clear data flow
✅ **Typed** - IDE autocomplete, type checking
✅ **Immutable** - No accidental mutations
✅ **Testable** - Easy to create test contexts
✅ **Separated** - Identity vs Domain concerns

