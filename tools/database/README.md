# Database Utility Scripts

This directory contains database management and debugging scripts for development.

## Scripts

### check_schema.py
Check the current database schema (tables, columns, and data types).

**Usage:**
```bash
python tools/database/check_schema.py
```

**Purpose:**
- Verify database schema after migrations
- Debug schema issues
- Compare expected vs actual schema

---

### reset_db.py
Reset the database by dropping all tables, functions, triggers, and alembic version.

**Usage:**
```bash
python tools/database/reset_db.py
```

**⚠️ Warning:** This will delete ALL data. Use only in development/testing environments.

**Purpose:**
- Clean slate for testing migrations
- Reset database to initial state
- Remove all schema objects

---

### fix_alembic_version.py
Manually fix the alembic version in the database (for development/debugging).

**Usage:**
```bash
python tools/database/fix_alembic_version.py
```

**Purpose:**
- Fix alembic version mismatches
- Debug migration issues
- Manually set migration state

---

## Common Workflows

### Reset and Re-run Migrations
```bash
# 1. Reset database
python tools/database/reset_db.py

# 2. Run migrations
alembic upgrade head

# 3. Verify schema
python tools/database/check_schema.py
```

### Check Schema After Migration
```bash
# Run migration
alembic upgrade head

# Verify schema
python tools/database/check_schema.py
```

---

## See Also

- [Alembic Migrations](../../alembic/) - Database migration files
- [PostgreSQL Guide](../../doc/guides/postgres.md) - Database standards
- [Testing Guide](../../TESTING.md) - Running tests

