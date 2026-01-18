# Mock Broker Configuration Guide

This guide explains how to configure the mock broker for different environments and testing scenarios.

---

## Overview

The Zerodha broker client has built-in mock mode that simulates real broker behavior without making actual API calls. This is controlled via environment variables and settings.

---

## Configuration Options

### Environment Variables

Add these to your `.env` file or export them:

```bash
# Enable/disable mock mode (default: true)
ZERODHA_USE_MOCK=true

# Mock scenario to simulate (default: success)
ZERODHA_MOCK_SCENARIO=success

# Real broker credentials (only needed when ZERODHA_USE_MOCK=false)
ZERODHA_API_KEY=your_api_key
ZERODHA_ACCESS_TOKEN=your_access_token
```

### Settings

These are defined in `config/settings.py`:

```python
class Settings(BaseSettings):
    # Broker Integration (optional)
    zerodha_api_key: str | None = None
    zerodha_access_token: str | None = None
    zerodha_use_mock: bool = True  # Mock mode by default
    zerodha_mock_scenario: str = "success"  # Default scenario
```

---

## Mock Scenarios

| Scenario | Description | Use Case |
|----------|-------------|----------|
| `success` | Orders complete successfully | Happy path testing |
| `partial_fill` | Limit orders partially fill (50%) | Test partial execution handling |
| `rejection` | Broker rejects orders | Test error handling |
| `network_error` | Simulates network timeouts | Test retry logic |
| `timeout` | Orders timeout without filling | Test timeout monitor |

---

## Configuration by Environment

### Development (Default)

**File:** `.env.local`

```bash
# Use mock mode with success scenario
ZERODHA_USE_MOCK=true
ZERODHA_MOCK_SCENARIO=success
```

**Behavior:**
- All orders complete successfully
- No real broker credentials needed
- Fast feedback for development

### Testing Different Scenarios

**Test partial fills:**
```bash
export ZERODHA_MOCK_SCENARIO=partial_fill
python -m pulse.background
```

**Test rejections:**
```bash
export ZERODHA_MOCK_SCENARIO=rejection
python -m pulse.background
```

**Test network errors:**
```bash
export ZERODHA_MOCK_SCENARIO=network_error
python -m pulse.background
```

### CI/CD Pipeline

**File:** `.env.ci`

```bash
# Always use mock mode in CI
ZERODHA_USE_MOCK=true
ZERODHA_MOCK_SCENARIO=success

# No real credentials needed
```

**Benefits:**
- No external dependencies
- Fast test execution
- Deterministic results
- No API rate limits

### Staging Environment

**Option 1: Mock mode for safety**
```bash
# Use mock mode to avoid real trades
ZERODHA_USE_MOCK=true
ZERODHA_MOCK_SCENARIO=success
```

**Option 2: Real broker with test account**
```bash
# Use real broker with Zerodha test account
ZERODHA_USE_MOCK=false
ZERODHA_API_KEY=your_test_api_key
ZERODHA_ACCESS_TOKEN=your_test_access_token
```

### Production Environment

**File:** `.env.production`

```bash
# Use real broker
ZERODHA_USE_MOCK=false

# Real credentials (from secrets manager)
ZERODHA_API_KEY=${ZERODHA_API_KEY_SECRET}
ZERODHA_ACCESS_TOKEN=${ZERODHA_ACCESS_TOKEN_SECRET}
```

**Important:**
- Never commit real credentials to git
- Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- Implement real KiteConnect calls before going to production

---

## How It Works

### Client Initialization

The execution worker reads settings and initializes the client:

```python
# pulse/workers/execution_worker.py
zerodha_client = ZerodhaClient(
    api_key=settings.zerodha_api_key or "mock_key",
    access_token=settings.zerodha_access_token,
    use_mock=settings.zerodha_use_mock,
    mock_scenario=settings.zerodha_mock_scenario
)
```

### Runtime Behavior

**When `use_mock=True`:**
- No real API calls are made
- Behavior is simulated based on `mock_scenario`
- Order IDs are generated locally
- State is tracked in memory

**When `use_mock=False`:**
- Real KiteConnect API calls are made
- Requires valid credentials
- Real orders are placed on broker
- Real money is at risk

---

## Testing Scenarios

### Test Success Scenario

```bash
# Set environment
export ZERODHA_USE_MOCK=true
export ZERODHA_MOCK_SCENARIO=success

# Run manual test
python tests/manual/test_mock_execution.py

# Or run full flow test
python scripts/test_execution_flow.py success
```

### Test All Scenarios

```bash
# Test each scenario
for scenario in success partial_fill rejection network_error timeout; do
    echo "Testing scenario: $scenario"
    python scripts/test_execution_flow.py $scenario
done
```

---

## Switching to Real Broker

### Step 1: Get Credentials

1. Sign up for Zerodha Kite Connect: https://kite.trade/
2. Create an app to get API key
3. Complete login flow to get access token
4. Store credentials securely

### Step 2: Update Environment

```bash
# .env.production
ZERODHA_USE_MOCK=false
ZERODHA_API_KEY=your_real_api_key
ZERODHA_ACCESS_TOKEN=your_real_access_token
```

### Step 3: Implement Real API Calls

Update `pulse/brokers/zerodha_client.py`:

```python
if not self.use_mock:
    # Uncomment and implement
    from kiteconnect import KiteConnect
    self.kite = KiteConnect(api_key=api_key)
    if access_token:
        self.kite.set_access_token(access_token)
```

Replace mock logic with real KiteConnect calls:
- `place_order()` → `kite.place_order()`
- `get_order_status()` → `kite.order_history()`
- `cancel_order()` → `kite.cancel_order()`

### Step 4: Test Carefully

1. Start with small quantities
2. Use Zerodha's test environment if available
3. Monitor logs closely
4. Have kill switch ready

---

## Troubleshooting

### Mock mode not working

**Check settings:**
```python
from config.settings import get_settings
settings = get_settings()
print(f"use_mock: {settings.zerodha_use_mock}")
print(f"scenario: {settings.zerodha_mock_scenario}")
```

### Wrong scenario being used

**Verify environment variable:**
```bash
echo $ZERODHA_MOCK_SCENARIO
```

**Restart worker after changing:**
```bash
# Kill existing worker
pkill -f "pulse.background"

# Start with new settings
export ZERODHA_MOCK_SCENARIO=partial_fill
python -m pulse.background
```

### Real broker calls failing

**Check credentials:**
```bash
echo $ZERODHA_API_KEY
echo $ZERODHA_ACCESS_TOKEN
```

**Verify mock mode is disabled:**
```bash
echo $ZERODHA_USE_MOCK  # Should be "false"
```

---

## Summary

✅ **Default:** Mock mode enabled (`ZERODHA_USE_MOCK=true`)  
✅ **Development:** Use mock mode with different scenarios  
✅ **CI/CD:** Always use mock mode  
✅ **Production:** Set `ZERODHA_USE_MOCK=false` and provide real credentials  

The mock broker provides a safe, fast, and deterministic way to develop and test the entire order execution flow without external dependencies.

