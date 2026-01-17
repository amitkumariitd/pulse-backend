# Split Order Feature - Phase 1: Order Splitting

## Overview
Enable users to place a single parent order that is automatically split into multiple child orders with scheduled execution times. This phase focuses on accepting the order and creating the split schedule. Execution will be handled in a separate feature.

---

## Table of Contents

1. **Business Context** - Problem, solution, users
2. **Functional Requirements** - Order modes, split configuration, behavior
3. **Data Model** - Parent/child tables, status flows, columns
4. **Splitting Algorithm** - Detailed calculation logic with time window constraints
5. **API Design** - Endpoint, request/response schemas, validation
6. **Processing Flow** - 2 phases: acceptance → splitting
7. **Multi-Pod Concurrency Safety** - Deduplication, locking, race condition prevention
8. **Implementation Checklist** - Database, API, workers, testing
9. **Out of Scope** - What's deferred to execution feature
10. **Questions to Resolve** - Open items for discussion

---

## Business Context

**Problem**:
- Large orders can move the market if executed at once
- Users need to spread orders over time to reduce market impact
- Predictable order patterns can be exploited by other traders

**Solution (Phase 1 - Splitting)**:
- Accept a parent order with split configuration
- Automatically split into multiple child orders
- Calculate scheduled execution times with randomization
- Store child orders ready for execution (execution handled separately)

**Users**:
- Traders placing large orders
- Algorithmic trading systems
- Users wanting to implement TWAP (Time-Weighted Average Price) strategies

---

## Functional Requirements

### 1. Order Placement

Users specify:
- **Instrument**: Trading symbol (e.g., "NSE:RELIANCE")
- **Side**: BUY or SELL
- **Total Quantity**: Number of shares to trade (e.g., 100 shares)

### 2. Split Configuration

Users must specify:
- **Number of splits**: How many child orders to create (e.g., 5 splits)
- **Total duration**: Time period over which to execute all splits (e.g., 60 minutes)
- **Randomization**: Add randomness to timing and quantity distribution

### 3. Split Behavior

**When Splitting Happens**:
- During Phase 2 (Order Splitting - Asynchronous)
- All calculations done upfront when creating child orders
- Each child order gets its `scheduled_at` timestamp calculated and stored

**Quantity Distribution**:
- Divide total quantity across child orders
- Apply randomization to avoid equal splits (e.g., not exactly 20, 20, 20, 20, 20)
- Ensure sum of child quantities = parent quantity (no rounding errors)
- Example: 100 shares, 5 splits → [18, 22, 19, 21, 20] instead of [20, 20, 20, 20, 20]

**Time Distribution** (Calculated during splitting):
- **Total time window**: From `parent.created_at` to `parent.created_at + duration_minutes`
- **Base interval**: `duration_minutes / (num_splits - 1)` (spread across duration)
- For each child order (sequence 0 to N-1):
  - Calculate base time: `parent.created_at + (sequence_number * base_interval)`
  - Apply randomization if enabled (within constraints)
  - Store as `child.scheduled_at`
- **Critical constraint**: ALL `scheduled_at` times MUST be within `[parent.created_at, parent.created_at + duration_minutes]`
- All `scheduled_at` times are calculated and stored when child orders are created

**Randomization Rules** (if `randomize = true`):
- **Quantity variance**: ±20% from average split size
  - Average = `total_quantity / num_splits`
  - Each child: `average ± random(0, 20%)`
  - Adjust last child to ensure sum = total_quantity
- **Time variance**: ±30% from scheduled interval
  - Base interval = `duration_minutes / (num_splits - 1)`
  - Each child: `base_time ± random(0, 30% of base_interval)`
  - **MUST enforce**: `scheduled_at >= parent.created_at`
  - **MUST enforce**: `scheduled_at <= parent.created_at + duration_minutes`
  - If randomization would violate bounds, clamp to valid range

**Example Calculation** (100 shares, 5 splits, 60 minutes, randomize=true):
```
Parent Order Created: 2025-12-29 10:00:00
Duration: 60 minutes
Time Window: 10:00:00 to 11:00:00 (HARD BOUNDARY)

Base interval = 60 / (5 - 1) = 15 minutes (spread across 4 intervals)
Average quantity = 100 / 5 = 20 shares

Splitting Algorithm Calculates:

Child 1 (sequence 0):
  - quantity = 18 (20 - 10% variance)
  - base_time = 10:00:00 + (0 * 15) = 10:00:00
  - scheduled_at = 10:00:00 (no variance for first)

Child 2 (sequence 1):
  - quantity = 22 (20 + 10% variance)
  - base_time = 10:00:00 + (1 * 15) = 10:15:00
  - variance = -3 min (within ±30% of 15 min)
  - scheduled_at = 10:12:00

Child 3 (sequence 2):
  - quantity = 19 (20 - 5% variance)
  - base_time = 10:00:00 + (2 * 15) = 10:30:00
  - variance = +2 min
  - scheduled_at = 10:32:00

Child 4 (sequence 3):
  - quantity = 21 (20 + 5% variance)
  - base_time = 10:00:00 + (3 * 15) = 10:45:00
  - variance = -4 min
  - scheduled_at = 10:41:00

Child 5 (sequence 4):
  - quantity = 20 (adjusted to make total = 100)
  - base_time = 10:00:00 + (4 * 15) = 11:00:00
  - variance = -2 min (ensure within boundary)
  - scheduled_at = 10:58:00

Validation:
✓ Total quantity: 18+22+19+21+20 = 100
✓ All scheduled_at within [10:00:00, 11:00:00] time window
✓ First child at 10:00:00 (start of window)
✓ Last child at 10:58:00 (before 11:00:00 boundary)
✓ Orders spread across the full 60-minute duration

These scheduled_at values are STORED in child_orders table during splitting.
```

---

## Data Model

### Status Flow Summary

**Parent Order Status (Splitting lifecycle)**:
- `status`: `PENDING` → `SPLITTING` → `SPLIT_COMPLETE` | `FAILED`

**Child Order Status (Ready for execution)**:
- `status`: `SCHEDULED` (ready to be picked up by execution worker)

**Key Principle**:
- Parent status tracks splitting process only
- Child status indicates readiness for execution
- Execution status tracking is out of scope for this phase

---

### Parent Order Table: `parent_orders`
Stores the original order request with split configuration. Tracks only the splitting process.

**Columns**:
- `id` (VARCHAR, PK) - Parent order ID
- `instrument` (VARCHAR) - Trading symbol (e.g., "NSE:RELIANCE")
- `side` (VARCHAR) - BUY or SELL
- `total_quantity` (INTEGER) - Total shares to trade
- `num_splits` (INTEGER) - Number of child orders to create
- `duration_minutes` (INTEGER) - Total duration in minutes
- `randomize` (BOOLEAN) - Whether to apply randomization
- `order_unique_key` (VARCHAR, unique) - Unique key for order deduplication

**Splitting Status**:
- `status` (VARCHAR) - Splitting lifecycle: `PENDING` | `SPLITTING` | `SPLIT_COMPLETE` | `FAILED`
- `failure_reason` (VARCHAR, nullable) - Error message if splitting failed

**Split Metadata**:
- `total_child_orders` (INTEGER) - Number of child orders created
- `split_completed_at` (TIMESTAMPTZ) - When child order creation completed

**Standard Columns**:
- Tracing: `trace_id`, `request_id`, `trace_source`
- Timestamps: `created_at`, `updated_at`

---

### Child Order Table: `child_orders`
Stores individual split orders ready for execution. Execution tracking is out of scope for this phase.

**Columns**:
- `id` (VARCHAR, PK) - Child order ID
- `parent_order_id` (VARCHAR, FK) - Reference to parent order
- `instrument` (VARCHAR) - Trading symbol (inherited from parent)
- `side` (VARCHAR) - BUY or SELL (inherited from parent)
- `quantity` (INTEGER) - Shares for this child order
- `sequence_number` (INTEGER) - Order in the split sequence (1, 2, 3...)

**Status**:
- `status` (VARCHAR) - Initial status: `SCHEDULED` (ready for execution worker to pick up)

**Scheduling**:
- `scheduled_at` (TIMESTAMPTZ) - When this order should execute (calculated during splitting)

**Standard Columns**:
- Tracing: `trace_id`, `request_id`, `trace_source`
- Timestamps: `created_at`, `updated_at`

**Note**: Execution-related columns (broker_order_id, execution_price, etc.) will be added in the execution feature.

---

## Splitting Algorithm (Detailed)

This algorithm runs during **Phase 2: Order Splitting** and calculates all quantities and execution times upfront.

### Input:
- `parent_order`: The parent order record
- `total_quantity`: Total shares to split
- `num_splits`: Number of child orders
- `duration_minutes`: Total duration window
- `randomize`: Boolean flag

### Output:
- Array of child order records with `quantity` and `scheduled_at` pre-calculated

### Algorithm Steps:

```python
def calculate_split_schedule(parent_order, total_quantity, num_splits, duration_minutes, randomize):
    """
    Calculate quantities and scheduled times for all child orders.
    All calculations done upfront during splitting phase.

    CRITICAL: All scheduled_at times MUST be within:
        [parent_order.created_at, parent_order.created_at + duration_minutes]
    """
    base_quantity = total_quantity / num_splits

    # Calculate interval to spread orders across FULL duration
    # Use (num_splits - 1) to spread from start to end of window
    base_interval_minutes = duration_minutes / (num_splits - 1) if num_splits > 1 else 0

    quantities = []
    scheduled_times = []

    # Step 1: Calculate quantities
    if randomize:
        # Apply ±20% variance
        for i in range(num_splits - 1):
            variance = random.uniform(-0.2, 0.2)
            qty = int(base_quantity * (1 + variance))
            quantities.append(qty)

        # Last child gets remainder to ensure exact total
        quantities.append(total_quantity - sum(quantities))
    else:
        # Equal distribution
        for i in range(num_splits - 1):
            quantities.append(int(base_quantity))
        quantities.append(total_quantity - sum(quantities))

    # Step 2: Calculate scheduled times
    parent_created_at = parent_order.created_at
    time_window_end = parent_created_at + timedelta(minutes=duration_minutes)

    for i in range(num_splits):
        # Base time spreads orders evenly across duration
        base_time = parent_created_at + timedelta(minutes=(i * base_interval_minutes))

        if randomize and i > 0 and i < num_splits - 1:  # Don't randomize first/last
            # Apply ±30% variance to interval
            max_variance = base_interval_minutes * 0.3
            variance_minutes = random.uniform(-max_variance, max_variance)
            scheduled_time = base_time + timedelta(minutes=variance_minutes)
        else:
            scheduled_time = base_time

        # ENFORCE HARD BOUNDARIES - MUST be within time window
        scheduled_time = max(scheduled_time, parent_created_at)
        scheduled_time = min(scheduled_time, time_window_end)

        scheduled_times.append(scheduled_time)

    # Step 3: Create child order records
    child_orders = []
    for i in range(num_splits):
        child = {
            'id': generate_id(),
            'parent_order_id': parent_order.id,
            'instrument': parent_order.instrument,
            'side': parent_order.side,
            'quantity': quantities[i],
            'sequence_number': i + 1,
            'scheduled_at': scheduled_times[i],  # ← STORED IN DATABASE
            'status': 'SCHEDULED',
            # ... tracing fields
        }
        child_orders.append(child)

    # Validation: Ensure all times within window
    assert all(parent_created_at <= t <= time_window_end for t in scheduled_times), \
        "All scheduled times must be within the duration window"

    return child_orders
```

### Key Constraints:

1. **Time Window Boundary** (HARD CONSTRAINT):
   ```
   parent.created_at <= child.scheduled_at <= parent.created_at + duration_minutes
   ```

2. **Interval Calculation**:
   - Use `duration_minutes / (num_splits - 1)` to spread across full duration
   - Example: 60 min, 5 splits → 60/4 = 15 min intervals
   - This ensures last order is at or near the end of the window

3. **Randomization Bounds**:
   - Variance is applied but then clamped to stay within window
   - First order typically at `parent.created_at` (start of window)
   - Last order at or near `parent.created_at + duration_minutes` (end of window)

4. **No Orders Outside Window**:
   - If randomization would push a time outside the window, it's clamped
   - This ensures 100% of orders execute within the specified duration

### Key Points:
1. **All calculations happen once** during splitting phase
2. **`scheduled_at` is persisted** in the database for each child
3. **Execution worker just reads** `scheduled_at` and executes when time comes
4. **No recalculation** needed during execution
5. **Deterministic**: Once split, the schedule is fixed
6. **Time window enforced**: ALL child orders MUST execute within `duration_minutes`

### Validation After Splitting:

After creating all child orders, the system MUST validate:

```python
def validate_split_schedule(parent_order, child_orders):
    """Validate that split schedule meets all constraints."""

    time_window_start = parent_order.created_at
    time_window_end = parent_order.created_at + timedelta(minutes=parent_order.duration_minutes)

    # 1. All scheduled times within window
    for child in child_orders:
        assert time_window_start <= child.scheduled_at <= time_window_end, \
            f"Child {child.id} scheduled_at {child.scheduled_at} outside window [{time_window_start}, {time_window_end}]"

    # 2. Total quantity matches
    total_qty = sum(child.quantity for child in child_orders)
    assert total_qty == parent_order.total_quantity, \
        f"Total child quantity {total_qty} != parent quantity {parent_order.total_quantity}"

    # 3. Correct number of children
    assert len(child_orders) == parent_order.num_splits, \
        f"Created {len(child_orders)} children, expected {parent_order.num_splits}"

    # 4. All children have valid sequence numbers
    sequences = sorted([child.sequence_number for child in child_orders])
    assert sequences == list(range(1, parent_order.num_splits + 1)), \
        f"Invalid sequence numbers: {sequences}"

    return True
```

---

## API Design

### Endpoint: Create Split Order

**GAPI Endpoint**: `POST /api/orders/split`

**Request Headers**:
- `Content-Type: application/json`
- `Authorization: Bearer <token>` (required)

**Request Body**:
```json
{
  "order_unique_key": "ouk_abc123xyz",
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "split_config": {
    "num_splits": 5,
    "duration_minutes": 60,
    "randomize": true
  }
}
```

**Response (Success - 202 Accepted)**:
```json
{
  "parent_order_id": "po_abc123",
  "status": "PENDING",
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "num_splits": 5,
  "duration_minutes": 60,
  "request_id": "r_xyz789",
  "trace_id": "t_xyz789"
}
```

**Error Responses**:
- `400 Bad Request` - Invalid input (missing fields, invalid values)
- `401 Unauthorized` - Missing or invalid auth token
- `409 Conflict` - Duplicate order_unique_key with different data
- `422 Unprocessable Entity` - Business validation failed (e.g., insufficient funds)

---

## Validation Rules

1. **Total Quantity**:
   - Must be > 0
   - Must be >= num_splits (to allow splitting)

2. **Split Configuration**:
   - `num_splits`: Must be between 2 and 100
   - `duration_minutes`: Must be between 1 and 1440 (24 hours)
   - `randomize`: Boolean, defaults to true

3. **Instrument**:
   - Must be valid format: `EXCHANGE:SYMBOL`
   - Exchange must be supported (NSE, BSE)

4. **Side**:
   - Must be "BUY" or "SELL"

---

## Processing Flow

### Phase 1: Order Acceptance (Synchronous - GAPI)
**Responsibility**: Accept and validate the order request

1. Validate request (schema, business rules)
2. Check order_unique_key for deduplication
3. Create parent order record:
   - `status = PENDING`
   - Store split configuration
4. Return `202 Accepted` immediately with `parent_order_id`

**Parent Status**: `PENDING`

---

### Phase 2: Order Splitting (Asynchronous - Pulse Background)
**Responsibility**: Split parent into child orders and calculate ALL execution schedules upfront

1. Pick parent orders where `status = PENDING`
2. Update parent: `status = SPLITTING`
3. **Calculate split quantities**:
   - Base quantity per child: `total_quantity / num_splits`
   - If `randomize = true`: Apply ±20% variance to each child
   - Adjust last child to ensure sum equals `total_quantity` exactly
   - Result: Array of quantities `[q1, q2, q3, ..., qN]`
4. **Calculate scheduled execution times** (THIS IS KEY):
   - Base interval: `duration_minutes / (num_splits - 1)` to spread across full duration
   - For each child (i = 0 to N-1):
     - Base time: `parent.created_at + (i * base_interval)`
     - If `randomize = true`: Apply ±30% variance to interval
     - Clamp to ensure within `[parent.created_at, parent.created_at + duration_minutes]`
     - Store as `scheduled_at[i]`
   - Result: Array of timestamps `[t1, t2, t3, ..., tN]`
5. **Create child order records**:
   - For each child (i = 0 to N-1):
     - `id` = generate unique ID
     - `parent_order_id` = parent.id
     - `instrument` = parent.instrument
     - `side` = parent.side
     - `quantity` = quantities[i]
     - `sequence_number` = i + 1
     - `scheduled_at` = timestamps[i]  ← **CALCULATED AND STORED**
     - `status` = SCHEDULED
     - Copy tracing fields from parent
6. **Validate split schedule**:
   - All scheduled_at times within time window
   - Total quantity matches parent quantity
   - Correct number of children created
7. Update parent order:
   - `status = SPLIT_COMPLETE`
   - `total_child_orders = num_splits`
   - `split_completed_at = NOW()`
8. If splitting fails (validation error, DB error, etc.):
   - Update parent: `status = FAILED`, set `failure_reason`

**Key Point**: All `scheduled_at` times are calculated and persisted during this phase. Child orders are ready for execution worker to pick up.

**Parent Status**: `PENDING` → `SPLITTING` → `SPLIT_COMPLETE` (or `FAILED`)
**Child Status**: `SCHEDULED` (with `scheduled_at` already set, ready for execution)

---

## Non-Functional Requirements

- **Deduplication**: Duplicate requests with same order_unique_key return same parent_order_id
- **Tracing**: All operations include trace_id, request_id for observability
- **History**: Both tables have history tables with triggers
- **Performance**: Order splitting should complete within 5 seconds
- **Concurrency Safety**: Multi-pod deployment safe (details below)

---

## Multi-Pod Concurrency Safety

**See**: `doc/guides/concurrency.md` for complete concurrency safety patterns.

### Problem Statement

In production, multiple pods (instances) run simultaneously:
- Multiple GAPI pods handling API requests
- Multiple Pulse Background Worker pods processing splits and executions

**Risks without proper safeguards**:
1. Duplicate splitting: Two workers create duplicate children
2. Duplicate execution: Two workers execute same child order twice
3. Race conditions: Concurrent updates to parent metrics
4. Lost updates: One pod's update overwrites another's

### Safety Mechanisms Applied

This feature implements the following patterns from `doc/guides/concurrency.md`:

#### 1. Idempotent API Operations (Pattern 1)

**Applied to**: `POST /api/orders/split` endpoint

**Implementation**: Use unique constraint on `order_unique_key` to prevent duplicate parent orders.

See `doc/guides/concurrency.md` - Pattern 1 for details.

---

#### 2. Pessimistic Locking for Splitting (Pattern 2)

**Applied to**: Background worker processing `parent_orders` with `status = PENDING`

**Implementation**: Use `SELECT FOR UPDATE SKIP LOCKED` to ensure only one pod processes each parent order.

**Key Query**:
```sql
SELECT * FROM parent_orders
WHERE status = 'PENDING'
ORDER BY created_at ASC
LIMIT 1
FOR UPDATE SKIP LOCKED
```

See `doc/guides/concurrency.md` - Pattern 2 for details.

---

#### 3. Timeout Monitors (Pattern 5)

**Applied to**: Recovery from pod crashes during splitting

**Implementation**: Periodic monitor to recover stuck records.

**Monitor**:
- Parent orders stuck in `SPLITTING` > 5 minutes → mark as `FAILED`

See `doc/guides/concurrency.md` - Pattern 5 for details.

**Note**: Execution-related concurrency patterns (optimistic locking, aggregate updates) will be covered in the execution feature.

---

### Database Indexes for Safety & Performance

```sql
-- Deduplication
CREATE UNIQUE INDEX idx_parent_orders_order_unique_key
ON parent_orders(order_unique_key);

-- Worker queries for splitting
CREATE INDEX idx_parent_orders_status_created
ON parent_orders(status, created_at)
WHERE status = 'PENDING';

-- Prevent duplicate sequences
CREATE UNIQUE INDEX idx_child_orders_parent_sequence
ON child_orders(parent_order_id, sequence_number);

-- Foreign key index
CREATE INDEX idx_child_orders_parent_id
ON child_orders(parent_order_id);
```

---

### Safety Summary

| Scenario | Risk | Solution | Guarantee |
|----------|------|----------|-----------|
| Duplicate API request | Duplicate parent orders | Unique order_unique_key | ✅ Only one parent created |
| Two pods split same parent | Duplicate children | SELECT FOR UPDATE SKIP LOCKED | ✅ Only one pod splits |
| Pod crashes during split | Orphaned SPLITTING | Timeout monitor | ✅ Eventually recovered |

---

## Out of Scope (Phase 1 - Splitting Only)

**Deferred to Execution Feature**:
- Executing child orders at scheduled times
- Broker integration and order placement
- Execution status tracking (READY, EXECUTING, EXECUTED, FAILED)
- Execution metrics (executed_child_orders, failed_child_orders, filled_quantity)
- Execution timestamps (execution_started_at, executed_at)
- Broker-related fields (broker_order_id, broker_status, execution_price)
- Retry logic for failed executions
- Timeout/expiration handling for unexecuted orders
- Cancellation of scheduled orders

**Also Out of Scope**:
- Price limit orders (only market orders)
- Modifying parent order after creation
- Order by amount mode (only quantity mode supported)

---

## Implementation Checklist

### Database Schema
- [ ] Create `parent_orders` table with all required columns
- [ ] Create `child_orders` table with all required columns
- [ ] Add unique constraint on `parent_orders.order_unique_key`
- [ ] Add unique constraint on `child_orders(parent_order_id, sequence_number)`
- [ ] Create indexes for worker queries
- [ ] Create history tables for both tables
- [ ] Create triggers for history tracking
- [ ] Write Alembic migration

### API Layer (GAPI)
- [ ] Implement `POST /api/orders/split` endpoint
- [ ] Validate request schema (order_unique_key, splits, duration)
- [ ] Check order_unique_key for deduplication before creating
- [ ] Handle UniqueViolationError gracefully
- [ ] Return 202 Accepted with parent_order_id
- [ ] Add request/response to API contract document

### Splitting Worker (Pulse Background)
- [ ] Implement splitting algorithm with time window constraints
- [ ] Use `SELECT FOR UPDATE SKIP LOCKED` to pick parent orders
- [ ] Update status to SPLITTING immediately
- [ ] Calculate quantities with randomization
- [ ] Calculate scheduled_at times within duration window
- [ ] Create all child orders in single transaction
- [ ] Update parent status to ACTIVE
- [ ] Handle errors and mark as FAILED

### Execution Worker (Pulse Background)
- [ ] Poll for child orders where `scheduled_at <= NOW()`
- [ ] Use atomic status transition (`WHERE status = 'SCHEDULED'`)
- [ ] Check UPDATE result to verify this pod won
- [ ] Execute order via broker API (or mock)
- [ ] Update child status to EXECUTED
- [ ] Update parent metrics by recalculating from children
- [ ] Handle errors and mark child as FAILED

### Timeout Monitors
- [ ] Monitor for stuck SPLITTING status (> 5 min)
- [ ] Monitor for stuck EXECUTING status (> 2 min)
- [ ] Mark stuck orders as FAILED with timeout reason
- [ ] Run monitors periodically

### Testing
- [ ] Unit test: Splitting algorithm (quantities, times, validation)
- [ ] Unit test: Time window constraint enforcement
- [ ] Integration test: Create split order via API
- [ ] Integration test: Duplicate request with same order_unique_key
- [ ] Integration test: Different data with same order_unique_key (409)
- [ ] Integration test: Full flow (acceptance → splitting → execution)
- [ ] Concurrency test: Two workers splitting same parent (only one succeeds)
- [ ] Concurrency test: Two workers executing same child (only one succeeds)
- [ ] Concurrency test: Concurrent metric updates (correct final count)
- [ ] Crash test: Worker crash during splitting (timeout recovery)
- [ ] Crash test: Worker crash during execution (timeout recovery)

### Documentation
- [ ] Update `doc/contract/gapi.md` with new endpoint
- [ ] Update `doc/contract/pulse.md` if needed
- [ ] Update `doc/contract/common.md` with new schemas

---

## Questions to Resolve

1. **Randomization Algorithm**: Confirm acceptable variance ranges (±20% quantity, ±30% time)?
2. **Partial Failures**: If some child orders fail, what happens to parent order status?
3. **Cancellation**: Should users be able to cancel parent order? Cancel remaining children?
4. **Minimum Split Size**: Should we enforce minimum quantity per child order (e.g., 1 share)?
