# PostgreSQL Rules (MANDATORY)

**Every database interaction MUST follow these rules. No exceptions.**

See `doc/standards/postgres.md` for detailed guide, examples, and best practices.

---

## What requires PostgreSQL compliance

- **New database tables** → schema standards (tracing columns, indexes, history table)
- **New repositories** → inherit from BaseRepository, use connection pooling
- **Database queries** → parameterized queries, context propagation
- **Schema changes** → Alembic migrations only
- **Database writes** → include trace_id and request_id, update history table

---

## Requirements

### Connection Management (mandatory)

- Use `asyncpg.create_pool()` for connection pooling
- Initialize pool in FastAPI lifespan (startup/shutdown)
- NEVER create direct connections in business logic
- Use `BaseRepository.get_connection()` and `release_connection()`

### Repository Pattern (mandatory)

- ALL database access MUST go through repositories
- Repositories MUST inherit from `BaseRepository`
- Repositories MUST accept `RequestContext` parameter
- Use try/finally to ensure connection release

**Example:**
```python
class OrderRepository(BaseRepository):
    async def create_order(self, order_data: dict, ctx: RequestContext) -> dict:
        conn = await self.get_connection()
        try:
            result = await conn.fetchrow(...)
            return dict(result)
        finally:
            await self.release_connection(conn)
```

### Tracing (non-negotiable)

- ALL tables MUST have `trace_id`, `request_id`, and `span_id` columns
- Async-initiating tables MUST also have `trace_source` column
- ALL database writes MUST include tracing values from `RequestContext`
- Pass `RequestContext` to ALL repository methods

**Required columns in every table:**
```sql
trace_id VARCHAR(64) NOT NULL,
request_id VARCHAR(64) NOT NULL,
span_id VARCHAR(16) NOT NULL
```

**Additional columns for async-initiating tables:**
```sql
trace_source VARCHAR(50) NOT NULL
```

**Required in every INSERT/UPDATE/DELETE:**

### Query Safety (mandatory)

- Use parameterized queries ONLY
- NEVER use f-strings or string interpolation for SQL
- Use transactions for multi-step operations
- Handle `asyncpg.PostgresError` exceptions

**✅ Good:**
```python
await conn.execute(
    "INSERT INTO orders (id, instrument) VALUES ($1, $2)",
    order_id, instrument
)
```

**❌ Bad (SQL Injection Risk):**
```python
await conn.execute(
    f"INSERT INTO orders (id, instrument) VALUES ('{order_id}', '{instrument}')"
)
```

### Schema Standards (mandatory)

**Required columns in ALL tables:**
- `id` - Primary key (VARCHAR or UUID)
- `created_at` - TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `updated_at` - TIMESTAMPTZ NOT NULL DEFAULT NOW()
- `trace_id` - VARCHAR(64) NOT NULL
- `request_id` - VARCHAR(64) NOT NULL
- `span_id` - VARCHAR(16) NOT NULL

**Additional columns for async-initiating tables:**
- `trace_source` - VARCHAR(50) NOT NULL

**Required indexes:**
- Primary key index (automatic)
- Index on `trace_id` for tracing queries
- Indexes on foreign keys
- Indexes on frequently filtered columns

### History Tables (mandatory)

**Every table MUST have a corresponding history table:**
- History table name: `{table_name}_history`
- Example: `orders` → `orders_history`

**History table requirements:**
- Contains ALL columns from main table
- Additional column: `history_id` (auto-increment primary key)
- Additional column: `operation` (VARCHAR: 'INSERT', 'UPDATE', 'DELETE')
- Additional column: `changed_at` (TIMESTAMPTZ NOT NULL DEFAULT NOW())

**Trigger requirements (mandatory):**
- Create trigger function to capture changes
- Create AFTER INSERT trigger
- Create AFTER UPDATE trigger
- Create AFTER DELETE trigger
- Triggers automatically populate history table

**Audit trail (automatic via triggers):**
- ALL INSERT operations → trigger inserts to history table
- ALL UPDATE operations → trigger inserts old values to history table
- ALL DELETE operations → trigger inserts deleted values to history table

### Migration Standards (mandatory)

- Use Alembic for ALL schema changes
- NEVER modify schema directly in production
- NEVER modify schema in application code
- Include both `upgrade()` and `downgrade()` functions

---

## Enforcement

If you write database code without following these rules:
1. You MUST refactor to use repository pattern
2. You MUST add tracing columns and context propagation
3. You MUST use parameterized queries
4. You MUST create Alembic migration for schema changes
5. You MUST create history table for every main table
6. You MUST create triggers to automatically populate history table

---

## When in doubt

- Re-read `doc/standards/postgres.md` for detailed examples
- Follow the BaseRepository pattern
- Always include RequestContext
- Ask for clarification instead of skipping requirements

