# Pulse Backend

Trading backend monorepo with three components:
- **GAPI**: External-facing gateway API
- **Pulse API**: Internal order management HTTP API
- **Pulse Background**: Background workers for async order processing

**Quick-start guides below. For detailed information, see:**
- `contracts/standards/` - Cross-service standards (database, testing, API, etc.)
- `doc/guides/` - Implementation guides (broker integration)
- `doc/examples/` - Context usage examples

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

## API Testing with Postman

### Quick Start

1. **Import collection:**
   - Open Postman → Import
   - Select `postman/pulse-backend.postman_collection.json`
   - Select `postman/local.postman_environment.json`

2. **Select environment:** "Pulse Backend - Local" (top-right dropdown)

3. **Test endpoints:**
   - Health Check → `GET /health`
   - Create Order → `POST /gapi/api/orders` (requires auth header)
   - Get Order → `GET /pulse/internal/orders/{order_id}`

**See:** [API Testing Standard](contracts/standards/api-testing/README.md) for best practices.

---

## IDE Setup (PyCharm)

### Quick Start

1. **Open project:** `File → Open → pulse-backend/`
2. **Set interpreter:** `Preferences → Python Interpreter → Add → Existing → .venv/bin/python`
3. **Use debug config:** Select "Pulse Backend - Debug" from dropdown (top-right)
4. **Start debugging:** Click debug button (bug icon) or `Ctrl+D`

**Breakpoint locations:**
- API routes: `pulse/api/routes.py`, `gapi/api/routes.py`
- Workers: `pulse/workers/splitting_worker.py`
- Repositories: `pulse/repositories/order_repository.py`

**See:** [IDE Setup Standard](contracts/standards/ide-setup/README.md) for debugging strategies.

---

## Database (PostgreSQL)

### Quick Start

**Connection:** Already configured in `pulse/infrastructure/database.py`

**Create new table:**
1. See SQL examples: `contracts/standards/database/examples/01-basic-table.sql`
2. Create migration: `alembic revision -m "create my_table"`
3. Copy from `contracts/standards/database/examples/03-migration.py`
4. Run: `alembic upgrade head`

**Create repository:**
1. Copy template: `contracts/standards/database/examples/04-repository.py`
2. Customize for your table
3. Use in routes via dependency injection

**See:**
- [Database Standard](contracts/standards/database/README.md) - Principles and patterns
- [Database Examples](contracts/standards/database/examples/) - SQL + Python templates

---

## Broker Integration (Zerodha)

### Mock Mode (Default)

For development and testing, mock mode is enabled by default:

```bash
# .env.local
ZERODHA_USE_MOCK=true
ZERODHA_MOCK_SCENARIO=success  # Options: success, partial_fill, rejection, timeout
```

**Test manually:**
```bash
python tests/manual/test_mock_execution.py
```

### Production Mode

For live trading with Zerodha:

```bash
# .env.production
ZERODHA_USE_MOCK=false
ZERODHA_API_KEY=your_api_key
ZERODHA_ACCESS_TOKEN=your_access_token
```

**See:** `doc/guides/broker-integration.md` for complete guide (mock mode, production setup, API usage)

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

