# Pulse Backend

Trading backend monorepo with two services:
- **GAPI**: External-facing gateway API
- **Order Service**: Internal order management service

## Quick Start (Unified Deployment)

Run both services together in a single process:

```bash
# Install dependencies
pip install -r requirements.txt

# Run unified app
uvicorn main:app --reload --port 8000
```

**Endpoints:**
- `GET /health` - Overall health check
- `GET /gapi/health` - GAPI health check
- `GET /gapi/api/hello` - GAPI hello endpoint
- `GET /order_service/health` - Order Service health check
- `GET /order_service/internal/hello` - Order Service hello endpoint

**Test:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/gapi/api/hello
curl http://localhost:8000/order_service/internal/hello
```

## Standalone Deployment

Each service can also run independently:

### GAPI
```bash
# Install dependencies from repo root
pip install -r requirements.txt

# Run GAPI
cd services/gapi
uvicorn main:app --reload --port 8000
```

See [services/gapi/README.md](services/gapi/README.md) for details.

### Order Service
```bash
# Install dependencies from repo root
pip install -r requirements.txt

# Run Order Service
cd services/order_service
uvicorn main:app --reload --port 8001
```

See [services/order_service/README.md](services/order_service/README.md) for details.

## Testing

Run all tests:
```bash
python -m pytest -v
```

See [TESTING.md](TESTING.md) for details.

---

## Architecture

Both services are:
- **Logically separate**: No shared code between services
- **Independently deployable**: Can run standalone or together
- **Future-proof**: Easy to split into separate repos

Service communication happens via HTTP APIs only.

