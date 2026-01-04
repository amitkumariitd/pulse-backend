# Pulse Backend

Trading backend monorepo with three components:
- **GAPI**: External-facing gateway API
- **Pulse API**: Internal order management HTTP API
- **Pulse Background**: Background workers for async order processing

## Requirements

- **Python 3.12+**
- **PostgreSQL 15+** (for production)
- **Docker** (optional, for containerized development)

## Quick Start

Run all three components in a single process:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up local configuration
cp .env.example .env.local
# Edit .env.local and set PULSE_DB_PASSWORD and other local values

# 3. Run unified app (GAPI + Pulse API + Background Workers)
./scripts/run_local.sh
```

**What runs:**
- ✅ GAPI (external gateway API)
- ✅ Pulse API (internal HTTP API)
- ✅ Pulse Background Workers (order splitting + timeout monitoring)

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

**Background workers** automatically process orders in the background. No separate process needed!

---

## Testing

Run all tests:
```bash
python -m pytest -v
```

See [TESTING.md](TESTING.md) for details.

---

## Architecture

**Current**: Single process running GAPI + Pulse API + Background Workers

**Future**: 3 deployables across 2 repos
- `pulse_api` - HTTP API (this repo)
- `pulse_background` - Background worker (this repo)
- `gapi` - Gateway (separate repo)

**Service Boundaries**:
- GAPI ↔ Pulse: HTTP only (different repos in future)
- Pulse API ↔ Pulse Background: Shared codebase (same service, different entry points)

