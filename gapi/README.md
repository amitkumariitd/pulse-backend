# GAPI

External-facing gateway API.

## Endpoints

- `GET /health` - Health check
- `GET /api/hello` - Hello endpoint
- `POST /api/orders` - Create order (proxies to Pulse)

## Deployment

Run from the repo root to deploy all components together (GAPI + Pulse API + Background Workers):

```bash
cd ..
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Access GAPI at: `http://localhost:8000/gapi/api/hello`

**What runs:**
- ✅ GAPI (this component)
- ✅ Pulse API (internal service)
- ✅ Background workers (automatic order processing)

**Benefits:**
- ✅ Single process for all components
- ✅ Background workers run automatically
- ✅ Shared database pool (more efficient)
- ✅ Simpler for development

## Testing

```bash
curl http://localhost:8000/gapi/health
curl http://localhost:8000/gapi/api/hello
```

