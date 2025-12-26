# Order Service

Internal service that owns the trading order domain.

## Endpoints

- `GET /health` - Health check
- `GET /internal/hello` - Hello endpoint

## Deployment Options

### Option 1: Unified Deployment (Recommended)

Run from the repo root to deploy both services together:

```bash
cd ../..
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Access Order Service at: `http://localhost:8000/order_service/internal/hello`

### Option 2: Standalone Deployment

Run Order Service independently:

```bash
# Install dependencies from repo root
pip install -r ../../requirements.txt

# Run from services/order_service directory
uvicorn main:app --reload --port 8001
```

Access Order Service at: `http://localhost:8001/internal/hello`

## Testing

**Unified mode:**
```bash
curl http://localhost:8000/order_service/health
curl http://localhost:8000/order_service/internal/hello
```

**Standalone mode:**
```bash
curl http://localhost:8001/health
curl http://localhost:8001/internal/hello
```

