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

**Two table categories:**

1. **Async-initiating tables** (spawn async work): `orders`, `jobs`, `tasks`
   - These tables trigger background/async processing
   - Need full tracing context for async workers

2. **All other tables**: `order_slices`, `executions`, `users`, `api_keys`, etc.
   - Either sync-only or created during async processing
   - Only need current request tracking

**Required columns in ALL tables:**
- `request_id` - Request identifier (pre-generated for async workers)

**Additional columns for async-initiating tables ONLY:**
- `origin_trace_id` - Trace ID that created this record
- `origin_trace_source` - Where the trace originated
- `origin_request_id` - Request ID that created this record
- `origin_request_source` - Where the request originated

**Why store origin context?**
- Audit trail: Know exactly which API call created this async work
- Debugging: Trace back from async worker to original request
- Compliance: Full lineage of who/what initiated the work

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

**Critical Rule for Modifying Tables:**

When adding/removing columns, you MUST update THREE things:
1. **Main table** - Add/remove the column
2. **History table** - Add/remove the same column
3. **Trigger function** - Update INSERT statements to include/exclude the column

**Missing any of these = broken history tracking or trigger errors!**

See `alembic/README` for detailed migration best practices and common mistakes.

---

## Schema Standards

### Required Columns (All Tables)
- `id` - Primary key (VARCHAR or UUID)
- `created_at` - TIMESTAMPTZ NOT NULL DEFAULT NOW(), auto-set by database
- `updated_at` - TIMESTAMPTZ NOT NULL DEFAULT NOW(), auto-updated by trigger
- `request_id` - VARCHAR(64) NOT NULL, request identifier

### Additional Columns (Async-Initiating Tables ONLY)
- `origin_trace_id` - VARCHAR(64) NOT NULL, trace ID that created this record
- `origin_trace_source` - VARCHAR(100) NOT NULL, where the trace originated
- `origin_request_id` - VARCHAR(64) NOT NULL, request ID that created this record
- `origin_request_source` - VARCHAR(100) NOT NULL, where the request originated

### Timestamp Format
**All timestamps MUST be stored as TIMESTAMPTZ:**
- Type: `TIMESTAMPTZ` (timestamp with time zone)
- Storage: 8 bytes (same as BIGINT)
- Precision: Microsecond (1/1,000,000 second)
- Timezone: Always stored in UTC, can be displayed in any timezone
- Range: 4713 BC to 294276 AD (sufficient for all use cases)

**Why TIMESTAMPTZ:**
- Native PostgreSQL type with full timezone support
- Automatic conversion to/from Python datetime objects (via asyncpg)
- No manual conversion needed in application code
- Human-readable in database queries and logs
- Standard PostgreSQL best practice
- Microsecond precision for high-frequency operations
- Efficient indexing and range queries

**Column definitions:**
```sql
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

**Auto-update trigger for updated_at:**
```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_{table_name}_updated_at
BEFORE UPDATE ON {table_name}
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

**Application code:**
- NEVER set `created_at` or `updated_at` in INSERT/UPDATE statements
- Database handles these automatically
- asyncpg automatically converts TIMESTAMPTZ to Python datetime objects
- All datetime objects are timezone-aware (UTC)

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

