# Pulse

Internal service that owns the trading order domain.

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

