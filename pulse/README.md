# Pulse

Internal service that owns the trading order domain.

## Components

Pulse consists of two deployable components:

1. **Pulse API** (`pulse/main.py`) - HTTP API for internal service-to-service communication
2. **Pulse Background** (`pulse/background.py`) - Background workers for async processing

## Endpoints

- `GET /health` - Health check
- `GET /internal/hello` - Hello endpoint

## Deployment Options

### Option 1: Unified Deployment (Recommended)

Run from the repo root to deploy both components together:

```bash
cd ..
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Access Pulse at: `http://localhost:8000/pulse/internal/hello`

### Option 2: Standalone Deployment

Run Pulse independently:

```bash
# Install dependencies from repo root
pip install -r ../requirements.txt

# Run from pulse directory
uvicorn main:app --reload --port 8001
```

Access Pulse at: `http://localhost:8001/internal/hello`

## Background Workers

The Pulse background worker processes pending orders and splits them into order slices.

### Running the Background Worker

```bash
# From repo root
python -m pulse.background
```

The worker will:
- Poll for orders with `order_queue_status = 'PENDING'`
- Use pessimistic locking (`SELECT FOR UPDATE SKIP LOCKED`) for concurrency safety
- Calculate split quantities and scheduled times using `pulse/splitting.py`
- Create order slices in the database
- Update parent order status to `COMPLETED` or `FAILED`

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

