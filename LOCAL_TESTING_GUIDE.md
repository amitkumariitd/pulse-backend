# Local Testing Guide - Split Order Feature

This guide will help you test the split order feature end-to-end on your laptop.

---

## Prerequisites

- Docker and Docker Compose installed
- Python 3.12+ (if running without Docker)
- PostgreSQL 15+ (if running without Docker)

---

## Option 1: Quick Test with Docker (Recommended)

### Step 1: Start Services

```bash
# Start PostgreSQL and the app
make up

# Check if services are running
make ps
```

This will start:
- PostgreSQL database on `localhost:5432`
- Pulse API on `http://localhost:8000`

### Step 2: Run Database Migrations

```bash
# Open a shell in the app container
make shell

# Inside the container, run migrations
alembic upgrade head

# Exit the container
exit
```

### Step 3: View Logs

```bash
# Watch application logs
make logs
```

### Step 4: Test the API

Open a new terminal and test order creation:

```bash
# Create a split order
curl -X POST http://localhost:8000/internal/orders \
  -H "Content-Type: application/json" \
  -H "X-Request-Id: r1234567890abcdef1234" \
  -H "X-Trace-Id: t1234567890abcdef1234" \
  -d '{
    "order_unique_key": "ouk_test_001",
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

Expected response (202 Created):
```json
{
  "order_id": "ord1735...",
  "order_queue_status": "PENDING",
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "num_splits": 5,
  "duration_minutes": 60,
  "randomize": true,
  "created_at": 1735...
}
```

### Step 5: Start the Splitting Worker

The splitting worker processes pending orders and creates child orders.

```bash
# In a new terminal, open shell in the container
make shell

# Inside the container, start the splitting worker
python -m pulse.background

# You should see logs like:
# {"level": "INFO", "message": "Starting Pulse background worker"}
# {"level": "INFO", "message": "Found pending orders", "data": {"count": 1}}
# {"level": "INFO", "message": "Order splitting completed", ...}
```

### Step 6: Verify the Results

Check the database to see the created child orders:

```bash
# Open PostgreSQL shell
make db-shell

# Inside psql, run queries:
```

```sql
-- View the parent order
SELECT id, instrument, side, total_quantity, num_splits, order_queue_status 
FROM orders 
WHERE order_unique_key = 'ouk_test_001';

-- View the child orders (slices)
SELECT id, order_id, sequence_number, quantity, status, scheduled_at
FROM order_slices 
WHERE order_id = '<order_id_from_above>'
ORDER BY sequence_number;

-- Verify quantities sum to total
SELECT order_id, COUNT(*) as num_slices, SUM(quantity) as total_quantity
FROM order_slices
WHERE order_id = '<order_id_from_above>'
GROUP BY order_id;

-- Exit psql
\q
```

### Step 7: Clean Up

```bash
# Stop all services
make down

# Or reset database (deletes all data)
make db-reset
```

---

## Option 2: Run Locally Without Docker

### Step 1: Start PostgreSQL

```bash
# If you have PostgreSQL installed locally
# Make sure it's running on localhost:5432
# with user: pulse, password: changeme, database: pulse
```

Or use Docker for just the database:

```bash
docker run -d \
  --name pulse-postgres \
  -e POSTGRES_USER=pulse \
  -e POSTGRES_PASSWORD=changeme \
  -e POSTGRES_DB=pulse \
  -p 5432:5432 \
  postgres:15-alpine
```

### Step 2: Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Run Migrations

```bash
# Make sure .env.local is configured correctly
alembic upgrade head
```

### Step 4: Start Pulse API

```bash
# Terminal 1: Start Pulse API
python -m pulse.main

# The API will start on http://localhost:8001
```

### Step 5: Start Splitting Worker

```bash
# Terminal 2: Start the background worker
python -m pulse.background
```

### Step 6: Test with curl

```bash
# Terminal 3: Create an order
curl -X POST http://localhost:8001/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "ouk_local_test_001",
    "instrument": "NSE:INFY",
    "side": "SELL",
    "total_quantity": 50,
    "num_splits": 10,
    "duration_minutes": 30,
    "randomize": false
  }'
```

Watch the logs in Terminal 2 to see the splitting worker process the order.

---

## Testing Scenarios

### Scenario 1: Basic Splitting (No Randomization)

```bash
curl -X POST http://localhost:8000/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "test_basic_001",
    "instrument": "NSE:TCS",
    "side": "BUY",
    "total_quantity": 100,
    "split_config": {
      "num_splits": 5,
      "duration_minutes": 60,
      "randomize": false
    }
  }'
```

Expected: 5 child orders with equal quantities (20 each)

### Scenario 2: Randomized Splitting

```bash
curl -X POST http://localhost:8000/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "test_random_001",
    "instrument": "NSE:RELIANCE",
    "side": "BUY",
    "total_quantity": 200,
    "split_config": {
      "num_splits": 10,
      "duration_minutes": 120,
      "randomize": true
    }
  }'
```

Expected: 10 child orders with varying quantities (±20% variance)

### Scenario 3: Duplicate Order Key (Idempotency Test)

```bash
# Create the same order twice
curl -X POST http://localhost:8000/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "test_duplicate_001",
    "instrument": "NSE:INFY",
    "side": "SELL",
    "total_quantity": 50,
    "split_config": {
      "num_splits": 5,
      "duration_minutes": 30,
      "randomize": false
    }
  }'

# Try again with the same order_unique_key
curl -X POST http://localhost:8000/internal/orders \
  -H "Content-Type: application/json" \
  -d '{
    "order_unique_key": "test_duplicate_001",
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

Expected: Second request returns 409 Conflict

---

## Verification Queries

### Check Order Status

```sql
-- View all orders
SELECT id, instrument, side, total_quantity, num_splits,
       order_queue_status, split_completed_at
FROM orders
ORDER BY created_at DESC
LIMIT 10;
```

### Check Child Orders

```sql
-- View all child orders for a specific parent
SELECT id, sequence_number, quantity, status,
       to_timestamp(scheduled_at / 1000000.0) as scheduled_time
FROM order_slices
WHERE order_id = '<your_order_id>'
ORDER BY sequence_number;
```

### Verify Time Window Constraint

```sql
-- Check that all scheduled times are within the duration window
WITH parent_info AS (
  SELECT id, created_at, duration_minutes
  FROM orders
  WHERE id = '<your_order_id>'
)
SELECT
  os.sequence_number,
  to_timestamp(os.scheduled_at / 1000000.0) as scheduled_time,
  to_timestamp(p.created_at / 1000000.0) as parent_created,
  to_timestamp(p.created_at / 1000000.0) + (p.duration_minutes || ' minutes')::interval as window_end,
  -- Check if within window
  CASE
    WHEN os.scheduled_at >= p.created_at
     AND os.scheduled_at <= p.created_at + (p.duration_minutes * 60 * 1000000)
    THEN 'VALID'
    ELSE 'INVALID'
  END as validation
FROM order_slices os
CROSS JOIN parent_info p
WHERE os.order_id = '<your_order_id>'
ORDER BY os.sequence_number;
```

### Verify Quantity Sum

```sql
-- Ensure child quantities sum to parent quantity
SELECT
  o.id as order_id,
  o.total_quantity as parent_quantity,
  COUNT(os.id) as num_slices,
  SUM(os.quantity) as total_slice_quantity,
  CASE
    WHEN o.total_quantity = SUM(os.quantity) THEN 'VALID'
    ELSE 'INVALID'
  END as validation
FROM orders o
LEFT JOIN order_slices os ON o.id = os.order_id
WHERE o.id = '<your_order_id>'
GROUP BY o.id, o.total_quantity;
```

---

## Troubleshooting

### Issue: "Connection refused" when calling API

**Solution**: Make sure the service is running
```bash
make ps  # Check if containers are running
make logs  # Check for errors
```

### Issue: "Database connection failed"

**Solution**: Check PostgreSQL is running
```bash
docker ps | grep postgres
# Or
make db-shell  # Try to connect
```

### Issue: Orders stuck in PENDING status

**Solution**: Make sure the splitting worker is running
```bash
# Check if worker is running in the logs
make logs

# Or start it manually
make shell
python -m pulse.background
```

### Issue: Migration errors

**Solution**: Reset the database and re-run migrations
```bash
make db-reset
make shell
alembic upgrade head
```

---

## Running Tests

```bash
# Run all tests
make test

# Run only integration tests
make test-int

# Run only unit tests
make test-unit

# Run specific test file
docker-compose -f deployment/docker/docker-compose.test.yml run --rm test \
  python -m pytest tests/integration/services/pulse/test_full_flow.py -v
```

---

## Next Steps

After verifying the split order feature works:

1. Test with GAPI (if implemented)
2. Test concurrency by creating multiple orders simultaneously
3. Monitor database history tables to see audit trail
4. Test error scenarios (invalid data, network failures, etc.)

---

## Useful Commands

```bash
# View all Docker logs
docker-compose -f deployment/docker/docker-compose.yml logs -f

# Restart just the app (not database)
docker-compose -f deployment/docker/docker-compose.yml restart app

# Execute SQL directly
docker exec -it pulse-postgres psql -U pulse -d pulse -c "SELECT COUNT(*) FROM orders;"

# Check database tables
docker exec -it pulse-postgres psql -U pulse -d pulse -c "\dt"
```

