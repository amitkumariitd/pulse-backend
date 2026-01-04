# Concurrency Safety Standards

## Overview

This document defines mandatory patterns for writing concurrent-safe code in multi-pod deployments.

**All features MUST follow these standards** to prevent:
- Duplicate processing
- Race conditions
- Lost updates
- Data corruption

---

## Core Principles

1. **Idempotency**: All state-changing operations must be idempotent
2. **Atomic Transitions**: Use database-level atomicity for state changes
3. **Pessimistic Locking**: Use row locks when exclusive access is required
4. **Optimistic Locking**: Use conditional updates for concurrent workers
5. **Source of Truth**: Derive aggregates from source data, never increment

---

## Pattern 1: Idempotent API Operations

**Use Case**: Prevent duplicate resource creation from retries or concurrent requests

**Implementation**:
```python
async def create_resource(data: dict, idempotency_key: str):
    """
    Create resource idempotently using unique constraint.
    """
    # Check for existing resource
    existing = await db.fetchrow(
        "SELECT * FROM resources WHERE idempotency_key = $1",
        idempotency_key
    )
    
    if existing:
        return existing  # Idempotent response
    
    # Try to create
    try:
        return await db.fetchrow(
            "INSERT INTO resources (..., idempotency_key) VALUES (..., $1) RETURNING *",
            idempotency_key
        )
    except UniqueViolationError:
        # Another pod created it concurrently, fetch and return
        return await db.fetchrow(
            "SELECT * FROM resources WHERE idempotency_key = $1",
            idempotency_key
        )
```

**Database Schema**:
```sql
CREATE TABLE resources (
    id VARCHAR(64) PRIMARY KEY,
    idempotency_key VARCHAR(64) NOT NULL,
    -- other columns
);

CREATE UNIQUE INDEX idx_resources_idempotency_key 
ON resources(idempotency_key);
```

**Guarantee**: ✅ Only one resource created per idempotency_key

---

## Pattern 2: Pessimistic Locking (Exclusive Processing)

**Use Case**: Background workers processing a queue where each item must be processed exactly once

**Implementation**:
```python
async def process_queue():
    """
    Process queue items with exclusive row-level locking.
    """
    while True:
        # Get one item with exclusive lock
        item = await db.fetchrow("""
            SELECT * FROM queue_items
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
            LIMIT 1
            FOR UPDATE SKIP LOCKED
        """)
        
        if not item:
            await asyncio.sleep(5)
            continue
        
        # This pod has exclusive lock - no other pod can process this item
        try:
            # Update status immediately
            await db.execute(
                "UPDATE queue_items SET status = 'PROCESSING' WHERE id = $1",
                item['id']
            )
            
            # Do the work
            result = await process_item(item)
            
            # Mark as complete
            await db.execute(
                "UPDATE queue_items SET status = 'COMPLETED', result = $1 WHERE id = $2",
                result, item['id']
            )
        except Exception as e:
            # Mark as failed
            await db.execute(
                "UPDATE queue_items SET status = 'FAILED', error = $1 WHERE id = $2",
                str(e), item['id']
            )
```

**Key Points**:
- `FOR UPDATE`: Acquires exclusive row lock
- `SKIP LOCKED`: Skips rows locked by other transactions
- Each pod processes different items
- No duplicate processing

**Guarantee**: ✅ Each item processed by exactly one pod

---

## Pattern 3: Optimistic Locking (Conditional Updates)

**Use Case**: Multiple workers competing for tasks where first-come-first-served is acceptable

**Implementation**:
```python
async def execute_tasks():
    """
    Execute tasks using optimistic locking (atomic status transition).
    """
    while True:
        # Find ready tasks (no lock on SELECT)
        ready_tasks = await db.fetch("""
            SELECT * FROM tasks
            WHERE status = 'READY'
              AND scheduled_at <= NOW()
            ORDER BY scheduled_at ASC
            LIMIT 10
        """)
        
        for task in ready_tasks:
            # Atomic status transition - only one pod succeeds
            result = await db.execute("""
                UPDATE tasks
                SET status = 'EXECUTING', started_at = NOW()
                WHERE id = $1 AND status = 'READY'
            """, task['id'])
            
            # Check if this pod won the race
            if result == "UPDATE 0":
                # Another pod already took this task, skip
                continue
            
            # This pod won - execute the task
            try:
                output = await execute_task(task)
                
                await db.execute("""
                    UPDATE tasks
                    SET status = 'COMPLETED', completed_at = NOW(), output = $1
                    WHERE id = $2
                """, output, task['id'])
            except Exception as e:
                await db.execute("""
                    UPDATE tasks
                    SET status = 'FAILED', error = $1
                    WHERE id = $2
                """, str(e), task['id'])
        
        await asyncio.sleep(10)
```

**Key Points**:
- `WHERE id = $1 AND status = 'READY'`: Conditional update
- Check `UPDATE` result to see if update succeeded
- If 0 rows updated, another pod won
- First pod to update wins, others skip

**Guarantee**: ✅ Each task executed by exactly one pod

---

## Pattern 4: Safe Aggregate Updates

**Use Case**: Updating counters or aggregates that multiple pods might update concurrently

**❌ WRONG - Race Condition**:
```python
# DON'T DO THIS - Lost updates!
await db.execute("""
    UPDATE parent_records
    SET processed_count = processed_count + 1
    WHERE id = $1
""", parent_id)
```

**✅ CORRECT - Recalculate from Source**:
```python
async def update_parent_metrics(parent_id: str):
    """
    Recalculate metrics from source of truth.
    Safe for concurrent execution.
    """
    # Query current state from child records
    metrics = await db.fetchrow("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
            COUNT(*) FILTER (WHERE status = 'FAILED') as failed
        FROM child_records
        WHERE parent_id = $1
    """, parent_id)
    
    # Update parent with calculated values
    await db.execute("""
        UPDATE parent_records
        SET 
            total_children = $1,
            completed_count = $2,
            failed_count = $3
        WHERE id = $4
    """, 
        metrics['total'],
        metrics['completed'],
        metrics['failed'],
        parent_id
    )
```

**Guarantee**: ✅ Metrics always accurate, no lost updates

---

## Pattern 5: Timeout Monitors (Crash Recovery)

**Use Case**: Recover from pod crashes that leave records in intermediate states

**Implementation**:
```python
async def monitor_stuck_records():
    """
    Periodic monitor to recover stuck records.
    Run every 1-5 minutes.
    """
    # Recover records stuck in PROCESSING
    await db.execute("""
        UPDATE queue_items
        SET status = 'FAILED',
            error = 'Processing timeout - worker may have crashed'
        WHERE status = 'PROCESSING'
          AND updated_at < NOW() - INTERVAL '5 minutes'
    """)
    
    # Recover records stuck in EXECUTING
    await db.execute("""
        UPDATE tasks
        SET status = 'FAILED',
            error = 'Execution timeout - worker may have crashed'
        WHERE status = 'EXECUTING'
          AND started_at < NOW() - INTERVAL '2 minutes'
    """)
```

**Guarantee**: ✅ System recovers from pod crashes

---

## Required Database Indexes

For efficient and safe concurrent operations:

```sql
-- Idempotency
CREATE UNIQUE INDEX idx_{table}_idempotency_key 
ON {table}(idempotency_key);

-- Worker queue queries
CREATE INDEX idx_{table}_status_created 
ON {table}(status, created_at) 
WHERE status IN ('PENDING', 'READY');

-- Timeout monitor queries
CREATE INDEX idx_{table}_status_updated 
ON {table}(status, updated_at)
WHERE status IN ('PROCESSING', 'EXECUTING');
```

---

## Testing Requirements

All concurrent code MUST have tests for:

1. **Idempotency Test**: Same request twice returns same result
2. **Concurrent Processing Test**: Two workers don't process same item
3. **Race Condition Test**: Concurrent updates produce correct final state
4. **Crash Recovery Test**: Timeout monitors recover stuck records

---

## Checklist for New Features

- [ ] API operations use idempotency_key with unique constraint
- [ ] Background workers use `FOR UPDATE SKIP LOCKED` or optimistic locking
- [ ] No incremental updates (e.g., `count = count + 1`)
- [ ] Aggregates recalculated from source of truth
- [ ] Timeout monitors for intermediate states
- [ ] Appropriate database indexes created
- [ ] Concurrency tests written and passing

---

## References

- PostgreSQL Row Locking: https://www.postgresql.org/docs/current/explicit-locking.html
- Idempotency Patterns: https://stripe.com/docs/api/idempotent_requests

