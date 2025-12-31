# Quick Start - Testing Split Order Feature

## ✅ Your System is Ready!

Everything is already set up and running:
- ✅ Docker containers running (pulse-backend + postgres)
- ✅ Database migrations applied
- ✅ API responding on http://localhost:8000

---

## Test the Feature (3 Simple Steps)

### Step 1: Create an Order

```bash
curl -X POST http://localhost:8000/pulse/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "my_test_order_001",
    "instrument": "NSE:RELIANCE",
    "side": "BUY",
    "total_quantity": 100,
    "num_splits": 5,
    "duration_minutes": 60,
    "randomize": true
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

### Step 2: Start the Splitting Worker

```bash
# In a new terminal
docker exec -it pulse-backend python -m pulse.background
```

**You'll see logs like:**
```
{"level": "INFO", "message": "Found pending orders", "data": {"count": 1}}
{"level": "INFO", "message": "Order splitting completed", "data": {"order_id": "...", "slices_created": 5}}
```

Press `Ctrl+C` to stop the worker when done.

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
    "num_splits": 5,
    "duration_minutes": 30,
    "randomize": false
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
    "num_splits": 20,
    "duration_minutes": 120,
    "randomize": true
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

**Problem:** API returns 500 error  
**Solution:** Restart the container: `docker restart pulse-backend`

**Problem:** Worker not processing orders  
**Solution:** Make sure worker is running: `docker exec -it pulse-backend python -m pulse.background`

**Problem:** Database connection error  
**Solution:** Check postgres is running: `docker ps | grep postgres`

---

## Next Steps

1. ✅ Test with GAPI endpoint: `POST /gapi/api/orders` (requires auth token)
2. ✅ Run integration tests: `make test-int`
3. ✅ Check the full testing guide: `LOCAL_TESTING_GUIDE.md`

---

## Success Criteria ✅

Your split order feature is working if:
- ✅ Orders are created with status `PENDING`
- ✅ Worker processes them and changes status to `COMPLETED`
- ✅ Child orders are created with correct quantities (sum = parent quantity)
- ✅ Scheduled times are within the duration window
- ✅ Duplicate `order_unique_key` returns 409 Conflict

