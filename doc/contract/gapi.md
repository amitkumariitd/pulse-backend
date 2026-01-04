# GAPI API Contract

GAPI is the external-facing gateway API.

**Architecture**: FastAPI monolith (one app)
**Routers**:
- `/api/*` - Public API endpoints (BFF)
- `/internal/*` - Internal service endpoints

**Authentication**: JWT auth (Bearer token)

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

#### `POST /api/orders`

Place an order that supports splitting into multiple slices executed over time.

**Request Headers**:
- `Content-Type: application/json` (required)
- `Authorization: Bearer <token>` (required)
- `X-Request-Id: <uuid>` (optional) - Auto-generated if not provided
- `X-Trace-Id: <uuid>` (optional) - Auto-generated if not provided

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
  - Must be unique per order
  - Used to prevent duplicate order submissions
  - If the same key is used with identical order data, returns existing order
  - If the same key is used with different order data, returns 409 Conflict
- `instrument` (string, required): Trading symbol in format `EXCHANGE:SYMBOL`
  - Supported exchanges: NSE, BSE
  - Example: `"NSE:RELIANCE"`, `"BSE:INFY"`
- `side` (string, required): Order side
  - Valid values: `"BUY"`, `"SELL"`
- `total_quantity` (integer, required): Total number of shares to trade
  - Must be > 0
  - Must be >= `num_splits` (to allow splitting)
- `split_config` (object, required): Split configuration
  - See `SplitConfig` schema in `common.md`

**Response Headers**:
- `X-Request-Id: <uuid>` - Request identifier
- `X-Trace-Id: <uuid>` - Trace identifier

**Response Body (202 Accepted)**:
```json
{
  "order_id": "ord_abc123",
  "order_unique_key": "test-order-123"
}
```

**Response Fields**:
- `order_id` (string): Unique identifier for the order (parent order)
- `order_unique_key` (string): Client-provided unique key (echoed from request)

**Error Responses**:

All error responses include tracing headers (`X-Request-Id`, `X-Trace-Id`) but NOT in the response body.

**400 Bad Request** - Invalid input
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Missing required field: instrument",
    "details": {
      "field": "instrument"
    }
  }
}
```

**400 Bad Request** - Invalid instrument format
```json
{
  "error": {
    "code": "INVALID_INSTRUMENT",
    "message": "Invalid instrument format. Expected EXCHANGE:SYMBOL",
    "details": {
      "instrument": "RELIANCE",
      "expected_format": "EXCHANGE:SYMBOL"
    }
  }
}
```

**400 Bad Request** - Invalid quantity
```json
{
  "error": {
    "code": "INVALID_QUANTITY",
    "message": "Total quantity must be >= num_splits",
    "details": {
      "total_quantity": 3,
      "num_splits": 5
    }
  }
}
```

**400 Bad Request** - Invalid split configuration
```json
{
  "error": {
    "code": "INVALID_SPLIT_CONFIG",
    "message": "num_splits must be between 2 and 100",
    "details": {
      "num_splits": 150,
      "min": 2,
      "max": 100
    }
  }
}
```

**401 Unauthorized** - Missing or invalid auth token
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Missing or invalid authentication token",
    "details": {}
  }
}
```

**409 Conflict** - Duplicate order_unique_key with different data
```json
{
  "error": {
    "code": "DUPLICATE_ORDER_UNIQUE_KEY",
    "message": "Order unique key already used with different request data",
    "details": {
      "order_unique_key": "ouk_abc123",
      "existing_order_id": "ord_xyz456"
    }
  }
}
```

**422 Unprocessable Entity** - Business validation failed
```json
{
  "error": {
    "code": "INSUFFICIENT_FUNDS",
    "message": "Insufficient funds to place order",
    "details": {
      "required": 100000,
      "available": 50000
    }
  }
}
```

**500 Internal Server Error** - System error
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "An unexpected error occurred",
    "details": {}
  }
}
```

---

## Validation Rules

### Instrument Validation
- Format: `EXCHANGE:SYMBOL`
- Supported exchanges: `NSE`, `BSE`
- Symbol: Alphanumeric, uppercase

### Quantity Validation
- Must be > 0
- Must be >= `num_splits` (to allow splitting)

### Split Configuration Validation
- `num_splits`:
  - Min: 2
  - Max: 100
- `duration_minutes`:
  - Min: 1
  - Max: 1440 (24 hours)
- `randomize`:
  - Boolean
  - Default: true

### Order Unique Key (Deduplication)
- Same `order_unique_key` with same request data → return existing parent order (202 Accepted)
- Same `order_unique_key` with different request data → return 409 Conflict
- The `order_unique_key` is mandatory and must be included in the request body

---

## Notes

- All split orders are processed asynchronously
- The API returns `202 Accepted` immediately after validation
- Actual splitting happens in the background (Pulse service)
- Use the `order_id` to track order status (future endpoint)

TODO:
- Add `GET /api/orders/{order_id}` to return the current `order_queue_status` and, when `SKIPPED`, an `order_queue_skip_reason` string.
