# Request Context Usage Examples

This document shows practical examples of using request context in the Pulse Backend.

## Table of Contents
1. [Basic Usage](#basic-usage)
2. [Context Enrichment](#context-enrichment)
3. [Service-to-Service Calls](#service-to-service-calls)
4. [FastAPI Dependencies](#fastapi-dependencies)
5. [Testing with Context](#testing-with-context)

---

## Basic Usage

### Automatic Context in Logs

Context is automatically injected into all logs. No manual calls needed!

```python
from fastapi import FastAPI
from shared.observability.middleware import ContextMiddleware
from shared.observability.logger import get_logger

app = FastAPI()
app.add_middleware(ContextMiddleware, service_name="gapi")

logger = get_logger("gapi")

@app.get("/api/orders")
def list_orders():
    # Context automatically included in logs!
    logger.info("Listing orders")
    
    # Log output includes: trace_id, request_id, user_id (if set), etc.
    return {"orders": []}
```

Context fields (`trace_id`, `request_id`, etc.) are automatically included in logs. See `doc/guides/logging.md` for format details.

---

## Context Enrichment

### Adding Domain Context

Enrich context with domain-specific IDs as you process the request:

```python
from shared.observability.context import set_context
from shared.observability.logger import get_logger

logger = get_logger("order_service")

@app.post("/internal/orders")
def create_order(order_data: dict):
    logger.info("Received order creation request")
    
    # Create order
    order = Order.create(order_data)
    
    # Enrich context with order_id
    set_context(order_id=order.id)
    
    # All subsequent logs automatically include order_id!
    logger.info("Order validated")
    logger.info("Order persisted")
    
    return {"order_id": order.id}
```

After enrichment, `order_id` is automatically included in all subsequent logs.

---

## Service-to-Service Calls

### Automatic Context Propagation

Use `ContextPropagatingClient` to automatically propagate context via HTTP headers:

```python
from shared.http.client import ContextPropagatingClient
from shared.observability.logger import get_logger

logger = get_logger("gapi")

# Create client
order_service = ContextPropagatingClient("http://localhost:8001")

@app.post("/api/orders")
async def create_order(order_data: dict):
    logger.info("Forwarding order to Order Service")
    
    # Context automatically propagated via headers!
    response = await order_service.post(
        "/internal/orders",
        json=order_data
    )
    
    return response.json()
```

**Headers Automatically Added:**
- `X-Trace-Id: t-8fa21c9d`
- `X-Request-Id: r-912873`
- `X-Trace-Source: GAPI:/api/orders`
- `X-Request-Source: GAPI:/api/orders`
- `X-User-Id: user_123` (if set)
- `X-Client-Id: tradingview` (if set)

---

## FastAPI Dependencies

### Using Context in Endpoints

Access context explicitly when needed:

```python
from fastapi import Depends
from shared.observability.dependencies import (
    get_request_context,
    require_user_id,
    get_optional_user_id
)

# Get complete context
@app.get("/api/orders")
def list_orders(ctx: dict = Depends(get_request_context)):
    logger.info("Listing orders")
    return {
        "orders": [],
        "request_id": ctx['request_id']
    }

# Require user_id (raises error if missing)
@app.post("/api/orders")
def create_order(
    order_data: dict,
    user_id: str = Depends(require_user_id)
):
    logger.info(f"Creating order for user {user_id}")
    return {"user_id": user_id}

# Optional user_id
@app.get("/api/public")
def public_endpoint(user_id: str | None = Depends(get_optional_user_id)):
    if user_id:
        logger.info("Authenticated request")
    else:
        logger.info("Anonymous request")
    return {"authenticated": user_id is not None}
```

---

## Testing with Context

### Integration Tests

Context works automatically in integration tests:

```python
from fastapi.testclient import TestClient

def test_context_propagation():
    # Arrange
    headers = {
        "X-Trace-Id": "t-test123",
        "X-Request-Id": "r-test456"
    }
    
    # Act
    response = client.get("/api/orders", headers=headers)
    
    # Assert
    assert response.headers["X-Trace-Id"] == "t-test123"
    assert response.headers["X-Request-Id"] == "r-test456"
```

### Unit Tests

Mock the logger to verify context injection:

```python
from unittest.mock import patch

@patch('my_module.logger')
def test_logging_with_context(mock_logger):
    # Act
    my_function()
    
    # Assert
    mock_logger.info.assert_called_once()
    # Context automatically injected by logger
```

---

## Advanced: Custom Metadata

### Adding Custom Metadata

```python
from shared.observability.context import set_context

@app.post("/api/webhook")
def handle_webhook(data: dict):
    # Add custom metadata
    set_context(metadata={
        "webhook_source": "tradingview",
        "webhook_version": "v2"
    })
    
    logger.info("Processing webhook")
    # Log includes metadata!
    
    return {"status": "accepted"}
```

---

## See Also

- [Context Standard](../standards/context.md) - Complete context specification
- [Logging Standard](../standards/logging.md) - Logging format
- [Tracing Standard](../standards/tracing.md) - Tracing semantics

