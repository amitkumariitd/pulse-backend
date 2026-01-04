# Pulse API Contract

Pulse is the internal service that owns the trading order domain.

**Architecture**: FastAPI monolith (one app)
**Routers**:
- `/internal/*` - Internal service endpoints (called by GAPI)

**Authentication**: None (internal service-to-service only)

---

## Endpoints

### Health Check

#### `GET /health`

Health check endpoint.

**Request**: None

**Response (200 OK)**:
```json
{
  "status": "ok"
}
```

---

### Order Management

#### `POST /internal/orders`

Create a new order in the database. This endpoint is called by GAPI after validation.

**Request Headers**:
- `Content-Type: application/json` (required)
- `X-Request-Id: <uuid>` (required) - Propagated from GAPI
- `X-Trace-Id: <uuid>` (required) - Propagated from GAPI
- `X-Parent-Span-Id: <uuid>` (optional) - For span hierarchy

**Request Body**:
```json
{
  "order_unique_key": "ouk_abc123xyz",
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "split_config": {
    "num_splits": 5,
    "duration_minutes": 60,
    "randomize": true
  }
}
```

**Request Fields**:
- `order_unique_key` (string, required): Unique key for order deduplication
- `instrument` (string, required): Trading symbol (e.g., "NSE:RELIANCE")
- `side` (string, required): Order side ("BUY" or "SELL")
- `total_quantity` (integer, required): Total shares to trade
- `split_config` (object, required): Split configuration
  - `num_splits` (integer, required): Number of child orders to create (2-100)
  - `duration_minutes` (integer, required): Total duration in minutes (1-1440)
  - `randomize` (boolean, required): Whether to apply randomization

**Response Headers**:
- `X-Request-Id: <uuid>` - Request identifier (echoed)
- `X-Trace-Id: <uuid>` - Trace identifier (echoed)

**Response Body (201 Created)**:
```json
{
  "order_id": "ord_abc123",
  "order_unique_key": "test-order-123"
}
```

**Response Fields**:
- `order_id` (string): Unique identifier for the order
- `order_unique_key` (string): Client-provided unique key (echoed from request)

**Error Responses**:

**409 Conflict** - Duplicate order_unique_key
```json
{
  "error": {
    "code": "DUPLICATE_ORDER_UNIQUE_KEY",
    "message": "Order unique key already exists",
    "details": {
      "order_unique_key": "ouk_abc123",
      "existing_order_id": "ord_xyz456"
    }
  }
}
```

**500 Internal Server Error** - Database error
```json
{
  "error": {
    "code": "DATABASE_ERROR",
    "message": "Failed to create order",
    "details": {}
  }
}
```

---

## Notes

- This endpoint is for internal use only (called by GAPI)
- GAPI performs all validation before calling this endpoint
- This endpoint assumes inputs are already validated
- Orders are created with `order_queue_status = 'PENDING'`
- Background worker picks up PENDING orders for splitting
