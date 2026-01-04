# PostgreSQL Examples

Complete, copy-paste ready examples for PostgreSQL implementation in Pulse.

---

## Files

### 1. `01-basic-table.sql`
**What**: Complete table schema with all required columns  
**Use**: Template for creating new tables  
**Includes**:
- Primary key
- Business columns
- Tracing columns (trace_id, request_id, tracing_source, request_source)
- Timestamp columns (created_at, updated_at)
- Required indexes
- Comments

---

### 2. `02-history-table.sql`
**What**: History table with trigger-based audit trail  
**Use**: Template for adding history to any table  
**Includes**:
- History table schema
- Trigger function (captures INSERT/UPDATE/DELETE)
- Triggers (automatic population)
- Clustered index on changed_at
- Comments

**Key Point**: Triggers handle history automatically - no application code needed!

---

### 3. `03-migration.py`
**What**: Complete Alembic migration  
**Use**: Template for creating migrations  
**Includes**:
- Main table creation
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

---

### 4. `04-repository.py`
**What**: Repository implementation with best practices  
**Use**: Template for creating repositories  
**Includes**:
- BaseRepository pattern
- Connection management
- Tracing context propagation
- Parameterized queries
- Error handling
- CRUD operations

**Key Point**: Repositories handle all database access - no direct queries in routes!

---

### 5. `05-connection-pool.py`
**What**: Connection pool setup with FastAPI  
**Use**: Template for database initialization  
**Includes**:
- Pool configuration
- FastAPI lifespan integration
- Dependency injection
- Health check endpoint

**Key Point**: Initialize pool once at startup, reuse across requests!

---

## Quick Start

### 1. Create a New Table

```bash
# 1. Copy 01-basic-table.sql and customize for your table
cp doc/examples/postgres/01-basic-table.sql my-table.sql

# 2. Copy 02-history-table.sql and customize
cp doc/examples/postgres/02-history-table.sql my-table-history.sql

# 3. Create migration
alembic revision -m "create my_table"

# 4. Copy code from 03-migration.py into migration file

# 5. Run migration
alembic upgrade head
```

### 2. Create a Repository

```bash
# 1. Copy 04-repository.py
cp doc/examples/postgres/04-repository.py pulse/repositories/my_repository.py

# 2. Customize for your table

# 3. Use in route handlers
```

### 3. Setup Connection Pool

```bash
# 1. Copy 05-connection-pool.py
cp doc/examples/postgres/05-connection-pool.py pulse/infrastructure/database.py

# 2. Configure settings in .env

# 3. Use in FastAPI app
```

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

- **Enforcement Rules**: `.augment/rules/postgres.md`
- **Standards**: `doc/guides/postgres.md`
- **Testing**: `.augment/rules/testing.md`

