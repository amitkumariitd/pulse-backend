# Testing Without Real Broker Integration

This guide explains how to test the order execution flow without connecting to a real broker (Zerodha).

---

## Overview

The `ZerodhaClient` has a built-in **mock mode** that simulates broker behavior without making real API calls. This allows you to:

- ✅ Test the entire execution flow end-to-end
- ✅ Simulate different scenarios (success, failures, partial fills)
- ✅ Develop and debug without broker credentials
- ✅ Run automated tests in CI/CD
- ✅ Avoid rate limits and API costs

---

## Mock Scenarios

The mock client supports multiple scenarios:

| Scenario | Behavior |
|----------|----------|
| `success` | Orders complete successfully (default) |
| `partial_fill` | Limit orders partially fill (50%) |
| `rejection` | Broker rejects orders (e.g., insufficient funds) |
| `network_error` | Simulates network timeouts |
| `timeout` | Orders timeout without filling |

---

## Quick Start

### 1. Run Manual Tests (No Database Required)

Test the mock client directly:

```bash
python tests/manual/test_mock_execution.py
```

This runs 4 test scenarios:
- Market order (immediate fill)
- Limit order (progressive fill over 3 polls)
- Partial fill (50% filled)
- Broker rejection

**Expected output:**
```
============================================================
MOCK EXECUTION FLOW TESTS
============================================================

============================================================
TEST 1: Market Order (Success)
============================================================
✓ Order placed: ZH240118abc12345
  Status: COMPLETE
  Filled: 100/100
  Price: ₹1250.00

✓ Market order test PASSED

...

============================================================
ALL TESTS PASSED ✓
============================================================
```

---

### 2. Run Unit Tests

All unit tests use mock mode by default:

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/brokers/test_zerodha_client.py

# Run with verbose output
pytest -v tests/unit/services/pulse/test_execution_worker.py
```

---

### 3. Test Full Execution Flow (Requires Database)

Test the complete flow with database:

```bash
# Success scenario (default)
python scripts/test_execution_flow.py success

# Partial fill scenario
python scripts/test_execution_flow.py partial_fill

# Rejection scenario
python scripts/test_execution_flow.py rejection
```

**What this does:**
1. Creates a test order slice in the database
2. Runs the execution worker with specified scenario
3. Shows the final slice and execution status

---

## Using Mock Client in Your Code

### Basic Usage

```python
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest
from shared.observability.context import RequestContext

# Create mock client
client = ZerodhaClient(
    api_key="test_key",
    access_token="test_token",
    use_mock=True,
    mock_scenario="success"  # or "partial_fill", "rejection", etc.
)

# Place order
request = ZerodhaOrderRequest(
    instrument="NSE:RELIANCE",
    side="BUY",
    quantity=100,
    order_type="MARKET"
)

response = await client.place_order(request, ctx)
print(f"Order ID: {response.broker_order_id}")
print(f"Status: {response.status}")
```

### Testing Different Scenarios

```python
# Test successful execution
client = ZerodhaClient(use_mock=True, mock_scenario="success")
response = await client.place_order(request, ctx)
assert response.status == "COMPLETE"

# Test partial fill
client = ZerodhaClient(use_mock=True, mock_scenario="partial_fill")
response = await client.place_order(request, ctx)
assert response.filled_quantity == 50  # 50% filled

# Test rejection
client = ZerodhaClient(use_mock=True, mock_scenario="rejection")
try:
    response = await client.place_order(request, ctx)
    assert False, "Should have raised exception"
except Exception as e:
    assert "INSUFFICIENT_FUNDS" in str(e)
```

---

## Mock Behavior Details

### Order Status Polling

The mock client simulates progressive filling:

```python
# Place limit order
response = await client.place_order(limit_order_request, ctx)
# Status: OPEN, Filled: 0

# Poll #1 (after 5 seconds)
status = await client.get_order_status(response.broker_order_id, ctx)
# Status: OPEN, Filled: 50 (partial)

# Poll #2 (after 10 seconds)
status = await client.get_order_status(response.broker_order_id, ctx)
# Status: OPEN, Filled: 50 (still partial)

# Poll #3 (after 15 seconds)
status = await client.get_order_status(response.broker_order_id, ctx)
# Status: COMPLETE, Filled: 100 (fully filled)
```

---

## Integration Tests

Run integration tests (requires database):

```bash
# Set up test database first
export PULSE_DB_HOST=localhost
export PULSE_DB_PORT=5432
export PULSE_DB_USER=pulse_user
export PULSE_DB_PASSWORD=pulse_password
export PULSE_DB_NAME=pulse_test

# Run migrations
alembic upgrade head

# Run integration tests
pytest tests/integration/
```

---

## Switching to Real Broker

When ready for production:

1. **Set environment variables:**
   ```bash
   export ZERODHA_API_KEY=your_real_api_key
   export ZERODHA_ACCESS_TOKEN=your_real_access_token
   ```

2. **Update client initialization:**
   ```python
   client = ZerodhaClient(
       api_key=settings.zerodha_api_key,
       access_token=settings.zerodha_access_token,
       use_mock=False  # Use real API
   )
   ```

3. **Implement real KiteConnect calls** in `pulse/brokers/zerodha_client.py`

---

## Troubleshooting

### "Module not found" errors
```bash
# Make sure you're in the project root
cd /path/to/pulse-backend

# Run with python -m
python -m tests.manual.test_mock_execution
```

### Database connection errors
```bash
# Check database is running
psql -h localhost -U pulse_user -d pulse_test

# Run migrations
alembic upgrade head
```

### Tests fail with "use_mock=False"
This is expected! Real KiteConnect integration is not yet implemented.
Always use `use_mock=True` for testing.

---

## Summary

✅ **For development**: Use `use_mock=True` (default)
✅ **For unit tests**: Mock mode is automatic
✅ **For integration tests**: Mock mode with real database
✅ **For production**: Set `use_mock=False` and implement real API calls

The mock client provides a complete simulation of broker behavior, allowing you to develop and test the entire execution flow without any external dependencies.
# Test rejection
client = ZerodhaClient(use_mock=True, mock_scenario="rejection")
try:
    response = await client.place_order(request, ctx)
    assert False, "Should have raised exception"
except Exception as e:
    assert "INSUFFICIENT_FUNDS" in str(e)
```

---

## Mock Behavior Details

### Market Orders
- **Success scenario**: Fills immediately with 100% quantity
- **Partial fill scenario**: Fills 50% immediately
- **Rejection scenario**: Raises exception
- **Network error scenario**: Raises timeout exception

### Limit Orders
- **Success scenario**:
  - Initially: OPEN, 0% filled
  - After 1 poll: OPEN, 50% filled
  - After 3 polls: COMPLETE, 100% filled
- **Partial fill scenario**: Fills 50% and stays OPEN
- **Timeout scenario**: Stays OPEN indefinitely

