# Pulse

Internal service that owns the trading order domain.

## Components

Pulse consists of two deployable components:

1. **Pulse API** (`pulse/main.py`) - HTTP API for internal service-to-service communication
2. **Pulse Background** (`pulse/background.py`) - Background workers for async processing

## Endpoints

- `GET /health` - Health check
- `GET /internal/hello` - Hello endpoint
- `POST /internal/orders` - Create order (internal only)

## Deployment

Run from the repo root to deploy all components together (GAPI + Pulse API + Background Workers):

```bash
cd ..
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Access Pulse at: `http://localhost:8000/pulse/internal/hello`

**What runs:**
- ✅ Pulse API (HTTP endpoints)
- ✅ Background Workers (order splitting + timeout monitoring)
- ✅ GAPI (external gateway)

**Benefits:**
- ✅ Single process for all components
- ✅ Background workers run automatically (no separate process needed)
- ✅ Shared database pool (more efficient)
- ✅ Simpler for development

---

## Background Workers

The Pulse background workers process pending orders and monitor for timeouts.

### Workers Included

1. **Splitting Worker** - Processes `PENDING` orders and creates order slices
2. **Timeout Monitor** - Recovers stuck `IN_PROGRESS` orders

### How It Works

**Splitting Worker:**
- Polls for orders with `order_queue_status = 'PENDING'`
- Uses pessimistic locking (`SELECT FOR UPDATE SKIP LOCKED`) for concurrency safety
- Calculates split quantities and scheduled times using `pulse/splitting.py`
- Creates order slices in the database
- Updates parent order status to `COMPLETED` or `FAILED`

**Timeout Monitor:**
- Checks for orders stuck in `IN_PROGRESS` state
- Recovers orders that exceed timeout threshold (default: 5 minutes)
- Marks them as `FAILED` for manual investigation

### Running Background Workers

Background workers start automatically when you run `uvicorn main:app`. No separate process needed!

### Configuration

- `poll_interval_seconds`: Time to wait between polls when no work found (default: 5)
- `batch_size`: Maximum orders to process per iteration (default: 10)

## Testing

**Unified mode:**
```bash
curl http://localhost:8000/pulse/health
curl http://localhost:8000/pulse/internal/hello
```

**Standalone mode:**
```bash
curl http://localhost:8001/health
curl http://localhost:8001/internal/hello
```

