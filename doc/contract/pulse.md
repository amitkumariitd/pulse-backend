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
  "num_splits": 5,
  "duration_minutes": 60,
  "randomize": true
}
```

**Request Fields**:
- `order_unique_key` (string, required): Unique key for order deduplication
- `instrument` (string, required): Trading symbol (e.g., "NSE:RELIANCE")
- `side` (string, required): Order side ("BUY" or "SELL")
- `total_quantity` (integer, required): Total shares to trade
- `num_splits` (integer, required): Number of child orders to create
- `duration_minutes` (integer, required): Total duration in minutes
- `randomize` (boolean, required): Whether to apply randomization

**Response Headers**:
- `X-Request-Id: <uuid>` - Request identifier (echoed)
- `X-Trace-Id: <uuid>` - Trace identifier (echoed)

**Response Body (201 Created)**:
```json
{
  "order_id": "ord_abc123",
  "order_queue_status": "PENDING",
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "num_splits": 5,
  "duration_minutes": 60,
  "randomize": true,
  "created_at": 1704067200000000
}
```

**Response Fields**:
- `order_id` (string): Unique identifier for the order
- `order_queue_status` (string): Current splitting lifecycle status (always "PENDING" on creation)
- `instrument` (string): Trading symbol (echoed from request)
- `side` (string): Order side (echoed from request)
- `total_quantity` (integer): Total quantity (echoed from request)
- `num_splits` (integer): Number of splits (echoed from request)
- `duration_minutes` (integer): Duration in minutes (echoed from request)
- `randomize` (boolean): Randomization flag (echoed from request)
- `created_at` (integer): Unix timestamp in microseconds

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
