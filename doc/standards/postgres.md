# PostgreSQL Standard

**Enforcement**: `.augment/rules/postgres.md`
**Examples**: `doc/examples/postgres/`

---

## Core Principles

### 1. Repository Pattern
**Why**: Testability, separation of concerns

- ALL database access through repositories
- Inherit from `BaseRepository`
- Accept `RequestContext` for tracing
- Use connection pooling (`asyncpg.Pool`)

**Example**: `doc/examples/postgres/04-repository.py`

---

### 2. Tracing
**Why**: Debug across services, audit trail

**Required columns** (every table):
- `request_id` - Request identifier
- `span_id` - Span identifier for this operation

**Additional columns** (async-initiating tables only):
- `trace_id` - Distributed tracing ID (needed for async continuation)
- `trace_source` - Where the trace originated (needed for async continuation)

**Example**: `doc/examples/postgres/01-basic-table.sql`

---

### 3. History Tables
**Why**: Audit trail, compliance, debugging

- Every table has `{table}_history`
- Triggers auto-populate (INSERT/UPDATE/DELETE)
- No manual history inserts

**Example**: `doc/examples/postgres/02-history-table.sql`

---

### 4. Query Safety
**Why**: Prevent SQL injection

- Parameterized queries ONLY
- NEVER f-strings or string interpolation
- Use transactions for multi-step ops

**Example**: `doc/examples/postgres/04-repository.py`

---

### 5. Schema Migrations
**Why**: Version control, safe deployments

- Use Alembic for ALL schema changes
- NEVER modify schema directly in production
- Include `upgrade()` and `downgrade()`

**Example**: `doc/examples/postgres/03-migration.py`

---

## Schema Standards

### Required Columns (All Tables)
- `id` - Primary key
- `created_at`, `updated_at` - Timestamps
- `trace_id`, `request_id`, `span_id` - Tracing

### Additional Columns (Async-Initiating Tables)
- `trace_source` - Origin of the trace (needed for async processes to continue the trace)

### Forbidden Columns
**NEVER store derived/aggregated data:**
- ❌ Counts that can be calculated (e.g., `total_child_orders`, `executed_child_orders`)
- ❌ Sums that can be calculated (e.g., `filled_quantity`, `total_amount`)
- ❌ Derived timestamps (e.g., `completed_at`, `expires_at` if calculable)

**Why**:
- Source of truth is the child records
- Prevents data inconsistency
- Aggregates should be calculated on-demand from source data
- Use database queries or application logic to compute these values

**Exception**: Caching columns are allowed ONLY if:
- Clearly marked as cache (e.g., `cached_total`)
- Have a documented refresh strategy
- Are not used as source of truth

### Required Indexes
- Primary key (automatic)
- `trace_id` (for tracing queries)
- Foreign keys
- Frequently filtered columns

### History Tables
- Table: `{table}_history`
- Triggers: AFTER INSERT/UPDATE/DELETE
- Index on `changed_at` (clustered)

---

## Connection Pooling

**Pattern**:
- `asyncpg.create_pool()` at startup
- Initialize in FastAPI lifespan
- `BaseRepository.get_connection()` / `release_connection()`

**Settings**:
- `min_size`: 10, `max_size`: 20
- `max_queries`: 50000
- `max_inactive_connection_lifetime`: 300s

**Example**: `doc/examples/postgres/05-connection-pool.py`

---

## Quick Reference

### Must Do
✅ Repository pattern
✅ Tracing columns
✅ History tables with triggers
✅ Parameterized queries
✅ Connection pooling
✅ Alembic migrations

### Must Not Do
❌ Direct DB access from routes
❌ SQL injection (f-strings)
❌ Manual history inserts
❌ Hardcoded credentials
❌ Direct schema changes in production
❌ Store derived/aggregated columns (counts, sums, calculated values)

