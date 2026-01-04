# Quick Start - Testing Split Order Feature

## Deployment Options

Choose how you want to run the application:

### Option 1: Local (Recommended - Simplest)

Run all components in a single process (GAPI + Pulse API + Background Workers):

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up local configuration
cp .env.example .env.local
# Edit .env.local and set PULSE_DB_PASSWORD

# 3. Run all components together
uvicorn main:app --reload --port 8000
```

**What runs:**
- ✅ GAPI (external gateway API)
- ✅ Pulse API (internal HTTP API)
- ✅ Background Workers (order splitting + timeout monitoring)

**Benefits:** Single process, background workers run automatically, no need for separate terminals!

---

### Option 2: Docker

Run with Docker Compose:

```bash
# Start all services
make up

# View logs
make logs
```

**What runs:**
- ✅ PostgreSQL database
- ✅ Pulse Backend (GAPI + Pulse API + Background Workers)

---

## Test the Feature (2 Simple Steps)

### Step 1: Create an Order

```bash
curl -X POST http://localhost:8000/pulse/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "my_test_order_001",
    "instrument": "NSE:RELIANCE",
    "side": "BUY",
    "total_quantity": 100,
    "split_config": {
      "num_splits": 5,
      "duration_minutes": 60,
      "randomize": true
    }
  }'
```

**Expected Response:**
```json
{
  "order_id": "ord...",
  "order_queue_status": "PENDING",
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "num_splits": 5,
  "duration_minutes": 60,
  "randomize": true,
  "created_at": 1767...
}
```

### Step 2: Watch Background Workers Process the Order

**If using Local mode:**
Background workers are already running! Check the logs in the same terminal.

**If using Docker:**
Background workers are already running! Check the logs with `make logs`.

**You'll see logs like:**
```
{"level": "INFO", "message": "Found pending orders", "data": {"count": 1}}
{"level": "INFO", "message": "Order splitting completed", "data": {"order_id": "...", "slices_created": 5}}
```

### Step 3: Verify the Results

```bash
# Check the parent order status
docker exec pulse-postgres psql -U pulse -d pulse -c \
  "SELECT id, order_queue_status, split_completed_at FROM orders WHERE order_unique_key = 'my_test_order_001';"

# View the child orders
docker exec pulse-postgres psql -U pulse -d pulse -c \
  "SELECT sequence_number, quantity, status, to_timestamp(scheduled_at / 1000000.0) as scheduled_time 
   FROM order_slices 
   WHERE order_id = (SELECT id FROM orders WHERE order_unique_key = 'my_test_order_001')
   ORDER BY sequence_number;"

# Verify quantities sum to 100
docker exec pulse-postgres psql -U pulse -d pulse -c \
  "SELECT SUM(quantity) as total, COUNT(*) as count 
   FROM order_slices 
   WHERE order_id = (SELECT id FROM orders WHERE order_unique_key = 'my_test_order_001');"
```

---

## What You Should See

✅ **Parent Order:**
- Status: `COMPLETED`
- `split_completed_at`: timestamp set

✅ **Child Orders (5 slices):**
- Sequence numbers: 1, 2, 3, 4, 5
- Quantities: Varying amounts (e.g., 16, 17, 22, 23, 22) due to randomization
- Total quantity: Exactly 100 (sum of all slices)
- Status: All `SCHEDULED`
- Scheduled times: Spread across 60 minutes from order creation

---

## Test Different Scenarios

### Without Randomization (Equal Splits)

```bash
curl -X POST http://localhost:8000/pulse/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "test_equal_splits",
    "instrument": "NSE:INFY",
    "side": "SELL",
    "total_quantity": 50,
    "split_config": {
      "num_splits": 5,
      "duration_minutes": 30,
      "randomize": false
    }
  }'
```

Expected: 5 slices with 10 shares each

### More Splits

```bash
curl -X POST http://localhost:8000/pulse/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "test_many_splits",
    "instrument": "NSE:TCS",
    "side": "BUY",
    "total_quantity": 200,
    "split_config": {
      "num_splits": 20,
      "duration_minutes": 120,
      "randomize": true
    }
  }'
```

Expected: 20 slices spread over 2 hours

### Test Idempotency (Duplicate Key)

```bash
# Create the same order twice
curl -X POST http://localhost:8000/pulse/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "duplicate_test",
    "instrument": "NSE:RELIANCE",
    "side": "BUY",
    "total_quantity": 100,
    "num_splits": 5,
    "duration_minutes": 60,
    "randomize": false
  }'

# Try again with same order_unique_key
curl -X POST http://localhost:8000/pulse/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "duplicate_test",
    "instrument": "NSE:RELIANCE",
    "side": "BUY",
    "total_quantity": 100,
    "num_splits": 5,
    "duration_minutes": 60,
    "randomize": false
  }'
```

Expected: Second request returns `409 Conflict`

---

## Useful Commands

### For Local Mode

```bash
# View all orders (requires local PostgreSQL)
psql -U pulse -d pulse -c \
  "SELECT id, instrument, side, total_quantity, num_splits, order_queue_status FROM orders ORDER BY created_at DESC LIMIT 10;"

# View all child orders
psql -U pulse -d pulse -c \
  "SELECT order_id, sequence_number, quantity, status FROM order_slices ORDER BY created_at DESC LIMIT 20;"

# Clear all data (reset)
psql -U pulse -d pulse -c "TRUNCATE orders, order_slices CASCADE;"
```

### For Docker Mode

```bash
# View all orders
docker exec pulse-postgres psql -U pulse -d pulse -c \
  "SELECT id, instrument, side, total_quantity, num_splits, order_queue_status FROM orders ORDER BY created_at DESC LIMIT 10;"

# View all child orders
docker exec pulse-postgres psql -U pulse -d pulse -c \
  "SELECT order_id, sequence_number, quantity, status FROM order_slices ORDER BY created_at DESC LIMIT 20;"

# Clear all data (reset)
docker exec pulse-postgres psql -U pulse -d pulse -c "TRUNCATE orders, order_slices CASCADE;"

# View application logs
docker logs pulse-backend --tail 50 -f

# Restart services
docker restart pulse-backend
```

---

## Troubleshooting

### Local Mode

**Problem:** API returns 500 error
**Solution:** Check the terminal logs for errors. Restart with `uvicorn main:app --reload --port 8000`

**Problem:** Background workers not processing orders
**Solution:** Workers run automatically. Check logs for errors.

**Problem:** Database connection error
**Solution:** Make sure PostgreSQL is running and `.env.local` has correct credentials.

### Docker Mode

**Problem:** API returns 500 error
**Solution:** Restart the container: `docker restart pulse-backend`

**Problem:** Background workers not processing orders
**Solution:** Workers run automatically. Check logs with `make logs`.

**Problem:** Database connection error
**Solution:** Check postgres is running: `docker ps | grep postgres`

---

## Next Steps

1. ✅ Test with GAPI endpoint: `POST /gapi/api/orders` (requires auth token)
2. ✅ Run integration tests: `make test-int` (Docker) or `python -m pytest tests/integration/ -v`
3. ✅ Check the full testing guide: `LOCAL_TESTING_GUIDE.md`

---

## Success Criteria ✅

Your split order feature is working if:
- ✅ Orders are created with status `PENDING`
- ✅ Background workers process them and change status to `COMPLETED`
- ✅ Child orders are created with correct quantities (sum = parent quantity)
- ✅ Scheduled times are within the duration window
- ✅ Duplicate `order_unique_key` returns 409 Conflict

---

## Deployment Mode Comparison

| Feature | Local | Docker |
|---------|-------|--------|
| **Simplicity** | ⭐⭐⭐ Easiest | ⭐⭐ Easy |
| **Background Workers** | Auto-start | Auto-start |
| **Database** | Local PostgreSQL | Docker PostgreSQL |
| **Terminals Needed** | 1 | 1 (+ docker) |
| **Production-like** | ❌ No | ✅ Yes |
| **Best For** | Quick testing | Full testing |

**Recommendation:** Start with **Local** for quick testing, then move to **Docker** for production-like testing.

