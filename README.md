# Pulse Backend

Trading backend monorepo with two components:
- **GAPI**: External-facing gateway API
- **Pulse**: Internal order management service

## Requirements

- **Python 3.12+**
- **PostgreSQL 15+** (for production)
- **Docker** (optional, for containerized development)

## Quick Start (Single Deployable)

Run both components together in a single process:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up local configuration
cp .env.example .env.local
# Edit .env.local and set PULSE_DB_PASSWORD and other local values

# 3. Run unified app
uvicorn main:app --reload --port 8000
```

**Endpoints:**
- `GET /health` - Overall health check
- `GET /gapi/health` - GAPI health check
- `GET /gapi/api/hello` - GAPI hello endpoint
- `GET /pulse/health` - Pulse health check
- `GET /pulse/internal/hello` - Pulse hello endpoint

**Test:**
```bash
curl http://localhost:8000/health
curl http://localhost:8000/gapi/api/hello
curl http://localhost:8000/pulse/internal/hello
```

## Standalone Deployment

Each component can also run independently:

### GAPI
```bash
# Install dependencies from repo root
pip install -r requirements.txt

# Run GAPI
cd gapi
uvicorn main:app --reload --port 8000
```

See [gapi/README.md](gapi/README.md) for details.

### Pulse
```bash
# Install dependencies from repo root
pip install -r requirements.txt

# Run Pulse
cd pulse
uvicorn main:app --reload --port 8001
```

See [pulse/README.md](pulse/README.md) for details.

## Testing

Run all tests:
```bash
python -m pytest -v
```

See [TESTING.md](TESTING.md) for details.

---

## Architecture

**Today**: Single deployable with two components (GAPI + Pulse)

**Future**: 3 deployables across 2 repos
- `pulse_api` - HTTP API (this repo)
- `pulse_background` - Background worker (this repo)
- `gapi` - Gateway (separate repo)

**Service Boundaries**:
- GAPI ↔ Pulse: HTTP only (different repos in future)
- Pulse API ↔ Pulse Background: Shared codebase (same service, different entry points)

