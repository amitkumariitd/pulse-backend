# PostgreSQL Examples - Python/asyncpg Implementation

Python-specific examples for PostgreSQL implementation in Pulse Backend.

**Standard**: See [Database Standard](../../contracts/standards/database/README.md) for cross-service principles.
**SQL Examples**: See [Database Examples](../../contracts/standards/database/examples/) for generic SQL table schemas.

---

## Files

### 1. `03-migration.py`
**What**: Python/Alembic migration template
**Use**: Template for creating database migrations in Pulse
**Includes**:
- Main table creation (using asyncpg)
- Indexes
- History table creation
- Trigger function
- Triggers
- Downgrade function

**Usage**:
```bash
alembic revision -m "create orders table"
# Copy code from this file into generated migration
alembic upgrade head
```

**Python-specific**: Uses Alembic (Python migration tool)

---

### 2. `04-repository.py`
**What**: Python/asyncpg repository implementation
**Use**: Template for creating repositories in Pulse
**Includes**:
- BaseRepository pattern (Python class)
- Connection management (asyncpg pool)
- Tracing context propagation (RequestContext)
- Parameterized queries (asyncpg syntax: $1, $2)
- Error handling (asyncpg.PostgresError)
- CRUD operations

**Key Point**: Repositories handle all database access - no direct queries in routes!

**Python-specific**: Uses asyncpg library, async/await syntax

---

### 3. `05-connection-pool.py`
**What**: Python/FastAPI connection pool setup
**Use**: Template for database initialization in Pulse
**Includes**:
- Pool configuration (asyncpg.create_pool)
- FastAPI lifespan integration
- Dependency injection (FastAPI Depends)
- Health check endpoint

**Key Point**: Initialize pool once at startup, reuse across requests!

**Python-specific**: Uses FastAPI framework, asyncpg library

---

## Quick Start

### 1. Create a New Table

```bash
# 1. See generic SQL examples in contracts
cat contracts/standards/database/examples/01-basic-table.sql
cat contracts/standards/database/examples/02-history-table.sql

# 2. Create Alembic migration
alembic revision -m "create my_table"

# 3. Copy code from 03-migration.py into migration file
# Customize table name and columns

# 4. Run migration
alembic upgrade head
```

### 2. Create a Repository

```bash
# 1. Copy Python repository template
cp doc/examples/postgres/04-repository.py pulse/repositories/my_repository.py

# 2. Customize for your table
# - Update class name
# - Update table name
# - Update column names
# - Add business logic methods

# 3. Use in route handlers via dependency injection
```

### 3. Setup Connection Pool (Already Done in Pulse)

Connection pool is already configured in `pulse/infrastructure/database.py`.

See `05-connection-pool.py` for reference if creating a new service.

---

## Customization Guide

### For a New Table

**Replace**:
- `orders` → your table name
- `orders_history` → your history table name
- `orders_history_trigger` → your trigger function name
- Column names → your business columns

**Keep**:
- All tracing columns (trace_id, request_id, tracing_source, request_source)
- All timestamp columns (created_at, updated_at)
- Trigger pattern (same for all tables)
- Index on trace_id

---

## Common Patterns

### Adding a Column

```sql
-- In migration upgrade()
op.execute("ALTER TABLE orders ADD COLUMN price DECIMAL(10,2)")

-- Also add to history table
op.execute("ALTER TABLE orders_history ADD COLUMN price DECIMAL(10,2)")

-- Update trigger function to include new column
```

### Adding an Index

```sql
-- In migration upgrade()
op.execute("CREATE INDEX idx_orders_instrument ON orders(instrument)")
```

### Querying History

```sql
-- Get all changes for an order (uses idx_orders_history_id)
SELECT * FROM orders_history
WHERE id = 'order-123'
ORDER BY changed_at DESC;

-- Get changes in last hour (uses idx_orders_history_changed_at)
SELECT * FROM orders_history
WHERE changed_at > NOW() - INTERVAL '1 hour'
ORDER BY changed_at DESC;

-- Get all updates (not inserts/deletes)
-- Note: No index on 'operation' - low cardinality, full table scan is acceptable
SELECT * FROM orders_history
WHERE operation = 'UPDATE'
ORDER BY changed_at DESC;
```

### History Table Indexes

**Required indexes**:
- `idx_orders_history_id` - For querying specific record's history
- `idx_orders_history_changed_at` - For time-based queries + CLUSTER

**NOT needed**:
- ~~`idx_orders_history_operation`~~ - Low cardinality (only 3 values: INSERT, UPDATE, DELETE)
  - Rarely queried alone
  - Index won't be used by query planner
  - Adds overhead without benefit

---

## See Also

- **Standard**: [Database Standard](../../contracts/standards/database/README.md)
- **SQL Examples**: [Database Examples](../../contracts/standards/database/examples/)
- **Implementation Guide**: `doc/guides/postgres-implementation.md`
- **Enforcement Rules**: `.augment/rules/postgres.md`
- **Testing**: `.augment/rules/testing.md`

