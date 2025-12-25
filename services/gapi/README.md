# GAPI

External-facing gateway API.

## Endpoints

- `GET /health` - Health check
- `GET /api/hello` - Hello endpoint

## Deployment Options

### Option 1: Unified Deployment (Recommended)

Run from the repo root to deploy both services together:

```bash
cd ../..
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Access GAPI at: `http://localhost:8000/gapi/api/hello`

### Option 2: Standalone Deployment

Run GAPI independently:

```bash
# From services/gapi directory
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Access GAPI at: `http://localhost:8000/api/hello`

## Testing

**Unified mode:**
```bash
curl http://localhost:8000/gapi/health
curl http://localhost:8000/gapi/api/hello
```

**Standalone mode:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/hello
```

