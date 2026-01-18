# Testing Without Real Broker

You can test the entire order execution flow **without connecting to Zerodha** using the built-in mock mode.

## Quick Test (No Database Required)

Run the manual test script:

```bash
python tests/manual/test_mock_execution.py
```

**Output:**
```
============================================================
MOCK EXECUTION FLOW TESTS
============================================================

============================================================
TEST 1: Market Order (Success)
============================================================
✓ Order placed: ZH2601182c90e691
  Status: COMPLETE
  Filled: 100/100
  Price: ₹1250.00

✓ Market order test PASSED

============================================================
TEST 2: Limit Order (Progressive Fill)
============================================================
✓ Order placed: ZH260118647b2419
  Status: OPEN
  Filled: 0/100

Poll #1:
  Status: OPEN
  Filled: 50/100
  Price: ₹1249.80

Poll #2:
  Status: OPEN
  Filled: 50/100
  Price: ₹1249.80

Poll #3:
  Status: COMPLETE
  Filled: 100/100
  Price: ₹1249.75

✓ Order completed after 3 polls

✓ Limit order test PASSED

============================================================
TEST 3: Partial Fill Scenario
============================================================
✓ Order placed: ZH2601184f78d229
  Status: OPEN
  Filled: 50/100 (50% partial fill)

✓ Partial fill test PASSED

============================================================
TEST 4: Broker Rejection Scenario
============================================================
✓ Order rejected as expected: INSUFFICIENT_FUNDS: Insufficient funds in account

✓ Rejection test PASSED

============================================================
ALL TESTS PASSED ✓
============================================================
```

---

## Run Unit Tests

All unit tests use mock mode automatically:

```bash
# Run all tests
pytest

# Run specific tests
pytest tests/unit/brokers/test_zerodha_client.py -v
pytest tests/unit/services/pulse/test_execution_worker.py -v
```

---

## Mock Scenarios

The mock client supports different scenarios:

| Scenario | Behavior |
|----------|----------|
| `success` | Orders complete successfully (default) |
| `partial_fill` | Limit orders partially fill (50%) |
| `rejection` | Broker rejects orders |
| `network_error` | Simulates network timeouts |
| `timeout` | Orders timeout without filling |

---

## Using Mock in Your Code

```python
from pulse.brokers.zerodha_client import ZerodhaClient, ZerodhaOrderRequest

# Create mock client
client = ZerodhaClient(
    api_key="test_key",
    access_token="test_token",
    use_mock=True,
    mock_scenario="success"  # Change scenario as needed
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

---

## Test with Database (Full Flow)

Test the complete execution flow with database:

```bash
# Success scenario
python scripts/test_execution_flow.py success

# Partial fill scenario
python scripts/test_execution_flow.py partial_fill

# Rejection scenario
python scripts/test_execution_flow.py rejection
```

This creates a real order slice in the database and runs the execution worker.

---

## What Gets Tested?

✅ **Order placement** - Market and limit orders  
✅ **Order polling** - Progressive filling over time  
✅ **Partial fills** - Orders that partially execute  
✅ **Broker rejections** - Insufficient funds, invalid params  
✅ **Network errors** - Timeouts and connection failures  
✅ **Execution worker** - Complete worker logic  
✅ **Timeout monitor** - Crash recovery  
✅ **Database operations** - All repository methods  

---

## When to Use Real Broker?

Only when you're ready for production:

1. Get real Zerodha API credentials
2. Set environment variables:
   ```bash
   export ZERODHA_API_KEY=your_real_api_key
   export ZERODHA_ACCESS_TOKEN=your_real_access_token
   ```
3. Update client initialization:
   ```python
   client = ZerodhaClient(
       api_key=settings.zerodha_api_key,
       access_token=settings.zerodha_access_token,
       use_mock=False  # Use real API
   )
   ```
4. Implement real KiteConnect calls in `pulse/brokers/zerodha_client.py`

---

## More Details

See [doc/guides/testing_without_broker.md](doc/guides/testing_without_broker.md) for comprehensive documentation.

---

## Summary

- ✅ Mock mode is **enabled by default**
- ✅ No broker credentials needed for testing
- ✅ All scenarios are covered (success, failures, partial fills)
- ✅ Works with unit tests, integration tests, and manual testing
- ✅ Safe to run in CI/CD pipelines

