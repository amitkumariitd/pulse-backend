# Pulse Backend - AI Assistant Guide

## Project Identity

**Backend application** for the Pulse trading platform. Python + FastAPI implementing:
- GAPI (External gateway API)
- Pulse API (Internal order management)
- Background workers (Order splitting, execution, timeout monitoring)

Built with async/await patterns, PostgreSQL with asyncpg, comprehensive distributed tracing, and strict service boundaries.

## Tech Stack Quick Reference

- **Language**: Python 3.12+
- **Framework**: FastAPI 0.128.0 + Uvicorn 0.40.0
- **Database**: PostgreSQL 15+ with asyncpg 0.31.0 (async) + Alembic 1.17.2 (migrations)
- **HTTP**: httpx 0.28.1 (async client)
- **Testing**: pytest 8.4.2 + pytest-asyncio 0.24.0
- **Config**: pydantic-settings 2.12.0
- **Broker**: kiteconnect 5.0.1 (Zerodha)

## Project Structure

```
pulse-backend/
├── gapi/              # External gateway API (port 8000)
│   ├── api/           # GAPI endpoints
│   ├── clients/       # HTTP client to Pulse
│   ├── models/        # GAPI Pydantic models
│   └── main.py        # GAPI FastAPI app
├── pulse/             # Internal order management (port 8001)
│   ├── api/           # Pulse API endpoints
│   ├── repositories/  # Data access layer
│   │   ├── order_repository.py
│   │   ├── order_slice_repository.py
│   │   └── broker_event_repository.py
│   ├── workers/       # Background async workers
│   │   ├── splitting_worker.py
│   │   ├── execution_worker.py
│   │   └── timeout_monitor.py
│   ├── brokers/       # Broker integrations (Zerodha)
│   ├── splitting.py   # Pure order splitting algorithm
│   └── main.py        # Pulse FastAPI app
├── shared/            # Shared utilities
│   ├── observability/ # Logging & tracing
│   │   ├── logger.py        # StructuredLogger
│   │   ├── context.py       # RequestContext
│   │   └── middleware.py    # ContextMiddleware
│   ├── database/      # DB utilities
│   │   ├── base_repository.py
│   │   └── pool.py          # Connection pooling
│   └── http/          # HTTP client utilities
├── config/            # Configuration
│   └── settings.py    # Pydantic Settings
├── alembic/           # Database migrations
├── tests/             # Test suite (111 tests)
│   ├── unit/          # Unit tests
│   └── integration/   # Integration tests
├── main.py            # Root entry point (mounts GAPI + Pulse)
└── requirements.txt
```

## Architecture & Service Boundaries

### Critical Rule (NON-NEGOTIABLE)

**GAPI ↔ Pulse communication is HTTP-only**

- GAPI **never** accesses Pulse database directly
- No shared code between services (except within Pulse API + Background)
- This separation enables future multi-repo split

### Services

**GAPI (Gateway API)** - port 8000:
- Base path: `/gapi/api/`
- Validates input, authenticates requests
- Forwards to Pulse via HTTP

**Pulse API** - port 8001:
- Base path: `/pulse/internal/`
- Full database access via asyncpg pool
- Creates and manages orders

**Background Workers** (Pulse service):
- **Splitting Worker**: Converts PENDING orders to slices (every 5s)
- **Execution Worker**: Executes slices via broker (every 5s)
- **Timeout Monitor**: Watches for stuck orders (every 60s)

All three workers share connection pool with Pulse API, run as async tasks in lifespan context.

## Database & Repository Pattern

### Connection Management

**asyncpg.Pool** for async connection pooling:
- Created in lifespan (startup)
- Global pool accessible via `get_db_pool()`
- Closed in lifespan (shutdown)

### Repository Pattern

All database access via **BaseRepository** class:
- Repositories manage connection acquisition/release
- Always use **parameterized queries** (never string interpolation)

**Key Repositories**:
- [OrderRepository](pulse/repositories/order_repository.py)
- [OrderSliceRepository](pulse/repositories/order_slice_repository.py)
- [BrokerEventRepository](pulse/repositories/broker_event_repository.py)
- [ExecutionRepository](pulse/repositories/execution_repository.py)

**Connection Acquisition**:
```python
async with pool.acquire() as conn:
    result = await conn.fetchrow("SELECT * FROM orders WHERE order_id = $1", order_id)
```

### Concurrency Safety

- **Idempotency**: `order_unique_key` unique constraint
- **Pessimistic locking**: `SELECT FOR UPDATE SKIP LOCKED` for exclusive processing
- **Timeout monitors**: Detect and recover from crashes

## Naming Conventions

### Domain Language (in code)

Use **domain language**, NOT service prefixes:
- ✅ `Order`, `OrderState`, `OrderSlice`, `process_order`
- ❌ `PulseOrder`, `process_pulse_service`, `GapiOrder`

### Service Language (at boundaries)

Service names at boundaries only:
- Directory names: `gapi/`, `pulse/`
- HTTP paths: `/gapi/api/`, `/pulse/internal/`

### ID Formats

- **Orders**: `ord{timestamp}{hex12}` (e.g., `ord1735228800a1b2c3d4e5f6`)
- **Order Slices**: `os{timestamp}{hex12}`
- **Trace IDs**: `t{timestamp}{hex12}`
- **Request IDs**: `r{timestamp}{hex12}`

### Code Style

- **snake_case**: functions, variables, modules (`create_order`, `order_repository`)
- **PascalCase**: classes (`Order`, `OrderRepository`, `RequestContext`)
- **UPPER_SNAKE_CASE**: constants (`MAX_BATCH_SIZE`, `DEFAULT_TIMEOUT`)

## Async Patterns

### Pure Async

**All I/O operations use async/await**:
- Database: `asyncpg` (never blocking psycopg2 in async context)
- HTTP requests: `httpx`
- Delays: `asyncio.sleep`

### Connection Pooling

Single `asyncpg.Pool` shared across app:
```python
async with pool.acquire() as conn:
    await conn.execute("INSERT INTO orders ...")
```

Repository pattern handles acquisition/release automatically.

### Background Workers

**Polling pattern**:
1. Fetch batch of work
2. Process batch
3. Sleep interval
4. Repeat

**Lifecycle**:
- Created in `lifespan` context manager
- Graceful shutdown: cancel and await tasks

**Example**:
```python
async def worker_loop(pool: asyncpg.Pool):
    while True:
        # Process batch
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM ... FOR UPDATE SKIP LOCKED LIMIT 10")
            # Process rows
        await asyncio.sleep(5)  # Sleep interval
```

## Distributed Tracing

### RequestContext (immutable dataclass)

```python
@dataclass(frozen=True)
class RequestContext:
    trace_id: str          # Global trace identifier (e.g., t1735228800a1b2c3d4e5f6)
    trace_source: str      # Origin (e.g., GAPI:POST/api/orders)
    request_id: str        # Per-request identifier
    request_source: str    # Current service/endpoint
    span_source: str       # Call chain (e.g., GAPI:POST/api/orders->PULSE:POST/internal/orders)
```

### Headers

**Tracing headers** (automatic via ContextMiddleware):
- `X-Trace-Id`: Global trace identifier (pass-through or generate)
- `X-Request-Id`: Per-request identifier
- `X-Trace-Source`: Trace origin
- `X-Request-Source`: Request source
- `X-Span-Source`: Service call chain

All headers echoed in response for observability.

### Logging

**StructuredLogger** ([shared/observability/logger.py](shared/observability/logger.py)):
- Outputs JSON to stdout
- Auto-injects tracing context (trace_id, request_id)
- **Security**: Sanitizes forbidden keys (authorization, token, password, secret, api_key)

**Usage**:
```python
logger = StructuredLogger(__name__)
logger.info("Order created", order_id=order_id, context=context)
```

**Reference**: pulse-contracts [`standards/tracing/README.md`](../pulse-contracts/standards/tracing/README.md)

## API Patterns

### Request/Response Models

**Pydantic BaseModel** for all DTOs:
- Field validation at model level
- Business logic validation in route handlers

**Example**:
```python
class CreateOrderRequest(BaseModel):
    order_unique_key: str
    instrument: str
    side: OrderSide  # Enum: BUY, SELL
    total_quantity: int
    split_config: SplitConfig
```

### Error Handling

**HTTPException** with nested error format:
```python
{
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": {...}
    }
}
```

**HTTP Status Codes**:
- `201 Created`: Resource created
- `202 Accepted`: Async processing started
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Auth failure
- `409 Conflict`: Duplicate (e.g., order_unique_key exists)
- `500 Internal Server Error`: System error

### Dependency Injection

**FastAPI `Depends()`**:
```python
@router.post("/orders")
async def create_order(
    request: CreateOrderRequest,
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    context = request.state.context  # RequestContext from middleware
    # ...
```

### Common Endpoints

- `POST /gapi/api/orders` → `202 Accepted` (GAPI forwards to Pulse)
- `POST /pulse/internal/orders` → `201 Created` (Pulse creates order)
- `GET /health`, `/gapi/health`, `/pulse/health` → Health checks

## Testing Standards

### Framework

**pytest** with **pytest-asyncio** for async tests.

### Organization

```
tests/
├── unit/            # Unit tests (no external dependencies)
│   ├── repositories/
│   ├── services/
│   └── shared/
└── integration/     # Integration tests (DB, HTTP)
    ├── database/
    └── services/
```

### Test Pattern (AAA)

```python
import pytest
from httpx import AsyncClient

async def test_create_order():
    # Arrange
    request = CreateOrderRequest(
        order_unique_key="test_key",
        instrument="RELIANCE",
        side=OrderSide.BUY,
        total_quantity=100,
        split_config=SplitConfig(num_splits=5, duration_minutes=30)
    )

    # Act
    async with AsyncClient(app=app) as client:
        response = await client.post("/pulse/internal/orders", json=request.dict())

    # Assert
    assert response.status_code == 201
    assert response.json()["order_id"].startswith("ord")
```

### Mocking

- **AsyncMock**: For async functions (`AsyncMock(return_value=...)`)
- **MagicMock**: For sync objects
- Mock DB pool, HTTP clients, broker clients

### Running Tests

```bash
./scripts/run_tests_local.sh -v          # All tests (111 tests)
./scripts/run_tests_local.sh tests/unit  # Unit only
pytest -k test_name                      # Single test
```

**Critical Rule**:
- All changes **MUST have tests**
- Tests **MUST pass** before marking work complete
- Never disable/skip tests to make builds pass

## Configuration Management

### Philosophy

- **Explicit configuration only** (no defaults)
- **Fail fast** on missing required config
- **Environment variables only** (no config files)

### Settings Class

[config/settings.py](config/settings.py) with pydantic-settings:
```python
@lru_cache
def get_settings() -> Settings:
    return Settings()  # Never auto-loads .env (intentional)
```

### Key Variables

**Core**:
- `ENVIRONMENT`: development/staging/production
- `SERVICE_NAME`: gapi/pulse
- `APP_HOST`, `APP_PORT`

**Database**:
- `PULSE_DB_HOST`, `PULSE_DB_PORT`
- `PULSE_DB_USER`, `PULSE_DB_PASSWORD`, `PULSE_DB_NAME`

**Logging**:
- `LOG_LEVEL`: ERROR/WARN/INFO/DEBUG
- `TRACING_ENABLED`: true/false

**Broker**:
- `ZERODHA_API_KEY`, `ZERODHA_ACCESS_TOKEN`
- `ZERODHA_USE_MOCK`: true/false
- `ZERODHA_MOCK_SCENARIO`: success/error/timeout

### Files

- `.env.example` - Template (committed)
- `.env.common` - Shared defaults (committed)
- `.env.local` - Local overrides (not committed, gitignored)

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic request/response models in `{service}/models/`
2. Create route handler in `{service}/api/`
3. Add route to FastAPI app
4. Add unit tests with mocked dependencies
5. Add integration tests with TestClient
6. Update pulse-contracts with API spec

### Adding a New Repository

1. Create class extending `BaseRepository`
2. Implement domain-specific query methods
3. Use **parameterized queries** (never string interpolation):
   ```python
   await conn.fetchrow("SELECT * FROM orders WHERE order_id = $1", order_id)
   ```
4. Add unit tests with mocked connection
5. Add integration tests with real DB

### Adding a New Background Worker

1. Create worker module in `pulse/workers/`
2. Implement polling loop with async/await
3. Use `SELECT FOR UPDATE SKIP LOCKED` for concurrency safety
4. Add to lifespan in [main.py](main.py)
5. Add tests with mocked DB and sleep

### Database Migration

1. Create migration: `alembic revision -m "add column to orders"`
2. Edit migration file in `alembic/versions/`
3. Apply locally: `alembic upgrade head`
4. Add `request_id` column to origin tables (tracing standard)
5. Add tests for new schema

## Background Workers

### Three Workers (in main.py lifespan)

1. **Splitting Worker** ([pulse/workers/splitting_worker.py](pulse/workers/splitting_worker.py))
   - Converts `PENDING` orders to slices every 5 seconds
   - Uses pure algorithm from [pulse/splitting.py](pulse/splitting.py)
   - Creates child `order_slices` with scheduled execution times

2. **Execution Worker** ([pulse/workers/execution_worker.py](pulse/workers/execution_worker.py))
   - Executes slices via broker every 5 seconds
   - Calls Zerodha API (or mock)
   - Records execution results in `broker_events` and `executions`

3. **Timeout Monitor** ([pulse/workers/timeout_monitor.py](pulse/workers/timeout_monitor.py))
   - Checks for stuck orders every 60 seconds
   - Marks as failed with timeout reason

### Pattern

**Polling loop**:
```python
async def worker(pool: asyncpg.Pool):
    while True:
        async with pool.acquire() as conn:
            # Fetch batch with pessimistic locking
            rows = await conn.fetch(
                "SELECT * FROM orders WHERE status = 'PENDING' "
                "FOR UPDATE SKIP LOCKED LIMIT 10"
            )
            for row in rows:
                # Process row
                pass
        await asyncio.sleep(5)  # Sleep interval
```

## Code Quality Rules

### Mandatory

1. **Service boundaries**: GAPI ↔ Pulse HTTP-only (NON-NEGOTIABLE)
2. **All database access via repositories** (never raw SQL in routes)
3. **Use domain language in code** (NO service prefixes like PulseOrder)
4. **All I/O operations async** (never blocking calls: requests, psycopg2)
5. **Parameterized queries only** (never string interpolation)
6. **All changes require tests** (unit + integration)
7. **Tests must pass** before marking work complete
8. **Explicit configuration** (fail fast on missing vars)
9. **Tracing context propagation** (via headers and RequestContext)

### Forbidden

1. GAPI accessing Pulse database directly
2. String interpolation in SQL queries: ❌ `f"SELECT * FROM orders WHERE order_id = '{order_id}'"`
3. Blocking I/O in async context: ❌ `requests.get()`, ❌ `psycopg2.connect()`
4. Disabling/skipping tests to make builds pass
5. Default configuration values (explicit only)
6. Logging sensitive data (tokens, passwords, API keys)
7. Service prefixes in domain code: ❌ `PulseOrder`, ❌ `process_pulse_service`

### Best Practices

- Keep route handlers thin (delegate to repository/service)
- Pure functions for business logic (e.g., [pulse/splitting.py](pulse/splitting.py))
- Use type hints throughout
- Descriptive variable names (avoid abbreviations)
- Docstrings for public functions

## Development Workflow

### Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env.local  # Edit with your values
```

### Running

```bash
# Run all services (GAPI + Pulse + Background workers)
python main.py

# Run specific service
uvicorn gapi.main:app --host 0.0.0.0 --port 8000
uvicorn pulse.main:app --host 0.0.0.0 --port 8001
```

### Testing

```bash
./scripts/run_tests_local.sh -v          # All tests (loads .env.local)
./scripts/run_tests_local.sh tests/unit  # Unit only
pytest -k test_name                      # Single test
pytest --cov=pulse --cov-report=html     # Coverage report
```

### Database

```bash
alembic upgrade head                  # Apply all migrations
alembic revision -m "description"     # Create new migration
alembic downgrade -1                  # Rollback one migration
```

### Linting (if configured)

```bash
black .          # Format code
mypy .           # Type checking
flake8 .         # Linting
```

## Debugging Tips

### Structured Logs

All logs output as JSON to stdout:
```json
{"timestamp": "2025-02-16T10:30:00Z", "level": "INFO", "logger": "pulse.api.orders", "message": "Order created", "trace_id": "t1735228800a1b2c3d4e5f6", "order_id": "ord1735228800123456"}
```

**Filter logs**:
```bash
tail -f logs.json | jq '. | select(.trace_id == "t123...")'
tail -f logs.json | jq '. | select(.level == "ERROR")'
```

### Database Queries

- Check slow queries in PostgreSQL logs
- Use `EXPLAIN ANALYZE` for query plans:
  ```sql
  EXPLAIN ANALYZE SELECT * FROM orders WHERE order_unique_key = 'test';
  ```
- Monitor connection pool usage (check asyncpg pool stats)

### Tracing Headers

- Check `X-Trace-Id` and `X-Request-Id` in HTTP responses
- Correlate frontend/backend logs via `trace_id`
- Use TracingDebugPanel in pulse-frontend to inspect headers

### Common Issues

- **Connection pool exhausted**: Increase pool size or check for connection leaks
- **Worker stuck**: Check timeout monitor logs, verify no long-running transactions
- **Duplicate orders**: Verify `order_unique_key` uniqueness before insert

## Documentation References

### Internal Docs

- [README.md](README.md) - Project overview and quick start
- [STRUCTURE.md](STRUCTURE.md) - Directory structure details
- [TESTING.md](TESTING.md) - Testing guide and standards
- [.augment/context.md](.augment/context.md) - Architecture and service boundaries
- [.augment/rules/rules.md](.augment/rules/rules.md) - Mandatory coding rules
- [doc/guides/broker-integration.md](doc/guides/broker-integration.md) - Broker setup

### External Standards (pulse-contracts)

- [`standards/tracing/README.md`](../pulse-contracts/standards/tracing/README.md) - Distributed tracing
- [`standards/context/README.md`](../pulse-contracts/standards/context/README.md) - Request context structure
- [`standards/logging/README.md`](../pulse-contracts/standards/logging/README.md) - Structured logging
- [`standards/concurrency/README.md`](../pulse-contracts/standards/concurrency/README.md) - Concurrency patterns
- [`standards/testing/README.md`](../pulse-contracts/standards/testing/README.md) - Testing standards
- [`service-groups/pulse-backend/services/gapi-api/api.md`](../pulse-contracts/service-groups/pulse-backend/services/gapi-api/api.md) - GAPI API spec
- [`service-groups/pulse-backend/services/pulse-api/api.md`](../pulse-contracts/service-groups/pulse-backend/services/pulse-api/api.md) - Pulse API spec
