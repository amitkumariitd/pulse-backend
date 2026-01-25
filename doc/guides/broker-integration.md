# Broker Integration Guide

Complete guide for broker integration with Zerodha, including mock mode for development and production setup.

---

## Overview

The `ZerodhaClient` in `pulse/brokers/zerodha_client.py` provides a unified interface for placing and monitoring orders. It supports:
- **Mock mode** (default) - For development and testing
- **Production mode** - For live trading with real Zerodha API

---

## Mock Mode (Development & Testing)

### Configuration

```bash
# .env.local
ZERODHA_USE_MOCK=true
ZERODHA_MOCK_SCENARIO=success  # See scenarios below
```

### Mock Scenarios

| Scenario | Behavior | Use Case |
|----------|----------|----------|
| `success` | Orders complete successfully | Happy path testing |
| `partial_fill` | Limit orders partially fill (50%) | Test partial execution |
| `rejection` | Broker rejects orders | Test error handling |
| `network_error` | Simulates network timeouts | Test retry logic |
| `timeout` | Orders timeout without filling | Test timeout monitor |

### Testing

**Run manual tests:**
```bash
python tests/manual/test_mock_execution.py
```

**Run unit tests:**
```bash
pytest tests/unit/brokers/test_zerodha_client.py
```

**Test specific scenario:**
```bash
export ZERODHA_MOCK_SCENARIO=partial_fill
python -m pulse.background
```

---

## Production Mode (Real Zerodha API)

---

### Prerequisites

**1. Install KiteConnect Library**

Already included in `requirements.txt`:
```bash
pip install -r requirements.txt
```

**2. Get Zerodha API Credentials**

- **API Key** - Get from Zerodha Developer Console
  - Sign up at: https://developers.kite.trade/
  - Create a new app
  - Note your API key

- **Access Token** - Generate via login flow
  - Zerodha uses OAuth2 for authentication
  - Access tokens expire daily and must be regenerated
  - See: https://kite.trade/docs/connect/v3/user/

### Configuration

```bash
# .env.production or environment variables
ZERODHA_API_KEY=your_api_key_here
ZERODHA_ACCESS_TOKEN=your_access_token_here
ZERODHA_USE_MOCK=false
```

**Important:** Access tokens expire daily. You must implement a token refresh mechanism.

---

## Usage

### Initialize Client

```python
from config.settings import get_settings
from pulse.brokers.zerodha_client import ZerodhaClient

settings = get_settings()

# Mock mode (development)
client = ZerodhaClient(
    api_key="test_key",
    use_mock=True,
    mock_scenario="success"
)

# Production mode
client = ZerodhaClient(
    api_key=settings.zerodha_api_key,
    access_token=settings.zerodha_access_token,
    use_mock=False
)
```

### Place Order

```python
from pulse.brokers.zerodha_client import ZerodhaOrderRequest
from shared.observability.context import RequestContext

# Create order request
order_request = ZerodhaOrderRequest(
    instrument="NSE:RELIANCE",
    side="BUY",
    quantity=100,
    order_type="LIMIT",
    limit_price=Decimal("1250.00"),
    product_type="CNC",
    validity="DAY"
)

# Place order
ctx = RequestContext(...)
response = await client.place_order(order_request, ctx)

print(f"Order ID: {response.broker_order_id}")
print(f"Status: {response.status}")
print(f"Filled: {response.filled_quantity}")
```

### Get Order Status

```python
# Poll order status
response = await client.get_order_status(broker_order_id, ctx)

print(f"Status: {response.status}")
print(f"Filled: {response.filled_quantity}/{response.filled_quantity + response.pending_quantity}")
print(f"Average Price: {response.average_price}")
```

### Cancel Order

```python
# Cancel order
response = await client.cancel_order(broker_order_id, ctx)

print(f"Status: {response.status}")
print(f"Filled before cancel: {response.filled_quantity}")
```

---

## Status Mapping

Zerodha statuses are mapped to our internal statuses:

| Zerodha Status | Our Status | Description |
|----------------|------------|-------------|
| `COMPLETE` | `COMPLETE` | Order fully filled |
| `OPEN` | `OPEN` | Order open at broker |
| `REJECTED` | `REJECTED` | Broker rejected order |
| `CANCELLED` | `CANCELLED` | Order cancelled |
| `TRIGGER PENDING` | `PENDING` | Trigger order pending |

---

## Error Handling

The client raises exceptions for errors:

```python
try:
    response = await client.place_order(order_request, ctx)
except Exception as e:
    if "INSUFFICIENT_FUNDS" in str(e):
        # Handle insufficient funds
        pass
    elif "NETWORK" in str(e):
        # Handle network error - retry
        pass
    else:
        # Handle other errors
        pass
```

Common error scenarios:
- **Insufficient funds** - Broker rejection (no retry)
- **Invalid instrument** - Broker rejection (no retry)
- **Network timeout** - Retryable error
- **Rate limit exceeded** - Retryable error

---

## Production Deployment

### 1. Set Environment Variables

```bash
export ZERODHA_API_KEY="your_api_key"
export ZERODHA_ACCESS_TOKEN="your_access_token"
export ZERODHA_USE_MOCK="false"
```

### 2. Token Refresh

Access tokens expire daily. Implement a refresh mechanism:

```python
# TODO: Implement token refresh
# - Store refresh token securely
# - Refresh before expiry
# - Update access token in settings
```

### 3. Rate Limiting

Zerodha has rate limits (3 requests/second). The execution worker respects these limits by:
- Polling every 5 seconds (not every second)
- Processing slices sequentially (not in parallel)

---

## References

- Zerodha KiteConnect Docs: https://kite.trade/docs/connect/v3/
- Python Library: https://github.com/zerodha/pykiteconnect
- API Console: https://developers.kite.trade/

