# Mock Broker Implementation

**Date:** 2026-01-18  
**Status:** Complete  
**Purpose:** Enable testing of order execution flow without real Zerodha integration

---

## Overview

Implemented a comprehensive mock mode for `ZerodhaClient` that simulates real broker behavior, allowing complete end-to-end testing without external dependencies.

---

## What Was Implemented

### 1. Mock Mode in ZerodhaClient

**File:** `pulse/brokers/zerodha_client.py`

**Features:**
- ✅ Mock mode enabled by default (`use_mock=True`)
- ✅ Configurable scenarios via `mock_scenario` parameter
- ✅ Realistic broker order ID generation
- ✅ Progressive filling simulation for limit orders
- ✅ Stateful order tracking across polling calls

**Supported Scenarios:**

| Scenario | Behavior |
|----------|----------|
| `success` | Orders complete successfully (default) |
| `partial_fill` | Limit orders fill 50% and stay OPEN |
| `rejection` | Broker rejects with INSUFFICIENT_FUNDS error |
| `network_error` | Simulates network timeout |
| `timeout` | Orders stay OPEN indefinitely |

### 2. Mock Behavior Details

**Market Orders:**
- Success: Immediate 100% fill
- Partial fill: Immediate 50% fill
- Rejection: Raises exception with error message
- Network error: Raises timeout exception

**Limit Orders:**
- Success scenario:
  - Poll 0 (placement): OPEN, 0% filled
  - Poll 1: OPEN, 50% filled (partial)
  - Poll 2: OPEN, 50% filled (still partial)
  - Poll 3: COMPLETE, 100% filled
- Partial fill scenario: 50% filled, stays OPEN
- Timeout scenario: Stays OPEN indefinitely

**Order Status Polling:**
- Tracks poll count per order
- Simulates progressive filling over time
- Maintains state between `place_order()` and `get_order_status()` calls

### 3. Testing Infrastructure

**Manual Test Script:**
- **File:** `tests/manual/test_mock_execution.py`
- **Purpose:** Quick verification without database
- **Tests:**
  - Market order (immediate fill)
  - Limit order (progressive fill over 3 polls)
  - Partial fill scenario
  - Broker rejection scenario

**Full Flow Test Script:**
- **File:** `scripts/test_execution_flow.py`
- **Purpose:** Test complete execution flow with database
- **Features:**
  - Creates real order slices in database
  - Runs execution worker with specified scenario
  - Shows final slice and execution status

**Documentation:**
- **File:** `TESTING_MOCK.md` - Quick reference guide
- **File:** `doc/guides/testing_without_broker.md` - Comprehensive guide

---

## Usage Examples

### Basic Mock Usage

```python
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest

# Create mock client
client = ZerodhaClient(
    api_key="test_key",
    access_token="test_token",
    use_mock=True,
    mock_scenario="success"
)

# Place order
request = ZerodhaOrderRequest(
    instrument="NSE:RELIANCE",
    side="BUY",
    quantity=100,
    order_type="MARKET"
)

response = await client.place_order(request, ctx)
# Returns: COMPLETE, 100% filled
```

### Testing Different Scenarios

```python
# Test partial fill
client = ZerodhaClient(use_mock=True, mock_scenario="partial_fill")
response = await client.place_order(limit_order_request, ctx)
assert response.filled_quantity == 50

# Test rejection
client = ZerodhaClient(use_mock=True, mock_scenario="rejection")
try:
    response = await client.place_order(request, ctx)
except Exception as e:
    assert "INSUFFICIENT_FUNDS" in str(e)
```

### Running Tests

```bash
# Quick manual test (no database)
python tests/manual/test_mock_execution.py

# Run unit tests
pytest tests/unit/brokers/test_zerodha_client.py -v

# Full flow test (with database)
python scripts/test_execution_flow.py success
python scripts/test_execution_flow.py partial_fill
python scripts/test_execution_flow.py rejection
```

---

## Implementation Details

### State Management

Mock orders are tracked in `_mock_order_states` dictionary:

```python
{
    "broker_order_id": {
        "status": "OPEN",
        "filled_quantity": 50,
        "pending_quantity": 50,
        "average_price": Decimal("1249.80"),
        "target_quantity": 100,
        "poll_count": 1
    }
}
```

### Progressive Filling Logic

For limit orders in success scenario:
- Poll count 0: 0% filled, OPEN
- Poll count 1: 50% filled, OPEN
- Poll count 2: 50% filled, OPEN
- Poll count 3+: 100% filled, COMPLETE

This simulates realistic market behavior where orders fill gradually.

### Broker Order ID Format

Generated IDs follow pattern: `ZH{YYMMDD}{8-char-hex}`

Example: `ZH2601182c90e691`

---

## Testing Coverage

✅ **Order placement** - Market and limit orders  
✅ **Order polling** - Progressive filling over time  
✅ **Partial fills** - Orders that partially execute  
✅ **Broker rejections** - Insufficient funds, invalid params  
✅ **Network errors** - Timeouts and connection failures  
✅ **Execution worker** - Complete worker logic  
✅ **Timeout monitor** - Crash recovery  
✅ **Database operations** - All repository methods  

---

## Migration Path to Real Broker

When ready for production:

1. **Get credentials:**
   ```bash
   export ZERODHA_API_KEY=your_real_api_key
   export ZERODHA_ACCESS_TOKEN=your_real_access_token
   ```

2. **Update initialization:**
   ```python
   client = ZerodhaClient(
       api_key=settings.zerodha_api_key,
       access_token=settings.zerodha_access_token,
       use_mock=False  # Switch to real API
   )
   ```

3. **Implement real KiteConnect calls** in `ZerodhaClient`:
   - Replace mock logic with actual `kite.place_order()` calls
   - Replace mock polling with actual `kite.order_history()` calls
   - Handle real error responses from Zerodha

---

## Benefits

✅ **No external dependencies** - Test without broker credentials  
✅ **Fast feedback** - No network latency or rate limits  
✅ **Deterministic** - Predictable behavior for testing  
✅ **Safe** - No risk of placing real orders  
✅ **CI/CD friendly** - Runs in automated pipelines  
✅ **Comprehensive** - Covers all scenarios (success, failures, edge cases)  

---

## Files Changed

- `pulse/brokers/zerodha_client.py` - Added mock mode implementation
- `tests/manual/test_mock_execution.py` - Manual test script (new)
- `scripts/test_execution_flow.py` - Full flow test script (new)
- `TESTING_MOCK.md` - Quick reference guide (new)
- `doc/guides/testing_without_broker.md` - Comprehensive guide (new)
- `doc/implementation/mock_broker_implementation.md` - This document (new)

---

## Test Results

All 95 unit tests pass:
```
tests/unit/ - 95 passed in 0.41s
```

Manual test output:
```
============================================================
ALL TESTS PASSED ✓
============================================================
```

---

## Next Steps

1. ✅ Mock implementation complete
2. ✅ Testing infrastructure in place
3. ✅ Documentation written
4. ⏳ Ready for integration testing with full execution flow
5. ⏳ Ready for real Zerodha integration when credentials available

