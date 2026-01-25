# IDE Setup - Pulse Backend

Pulse-specific guide for IDE configuration and debugging.

**Standard:** See [IDE Setup Standard](../../contracts/standards/ide-setup/README.md) for cross-service debugging best practices.

---

## PyCharm Setup

### 1. Open Project

```bash
# Open PyCharm
# File → Open → Select pulse-backend directory
```

### 2. Configure Python Interpreter

1. **PyCharm → Preferences** (Cmd+,)
2. **Project: pulse-backend → Python Interpreter**
3. Click **gear icon** → **Add Interpreter** → **Add Local Interpreter**
4. Select **Existing environment**
5. Browse to: `/Users/amitkumar/learn/pulse-backend/.venv/bin/python`
6. Click **OK**

### 3. Use Debug Configuration

The debug configuration is already created at `.idea/runConfigurations/Pulse_Backend_Debug.xml`

1. Look at top-right corner of PyCharm
2. Select **"Pulse Backend - Debug"** from dropdown
3. Click the **Debug** button (bug icon) or press **Ctrl+D**

---

## Setting Breakpoints

### Pulse-Specific Breakpoint Locations

**API Endpoints:**
```python
# File: pulse/api/routes.py
@router.post("/internal/orders")
async def create_order(request: CreateOrderRequest, ctx: RequestContext = Depends(get_request_context)):
    # Set breakpoint here ← Click in gutter
    logger.info(f"Creating order: {request.instrument}")
```

**Background Workers:**
```python
# File: pulse/workers/splitting_worker.py
async def process_pending_orders(self):
    # Set breakpoint here ← Click in gutter
    logger.info("Splitting worker: Checking for pending orders")
```

**Repositories:**
```python
# File: pulse/repositories/order_repository.py
async def create_order(self, order_data: dict, ctx: RequestContext) -> dict:
    # Set breakpoint here ← Click in gutter
    conn = await self.get_connection()
```

**Service Layer:**
```python
# File: pulse/services/order_service.py
async def split_order(self, order_id: str, ctx: RequestContext):
    # Set breakpoint here ← Click in gutter
    order = await self.order_repo.get_order_by_id(order_id, ctx)
```

---

## Debug Workflow

### 1. Start Debug Mode

- Click **Debug** button (bug icon) or **Ctrl+D**
- Wait for app to start
- Console shows: `Uvicorn running on http://0.0.0.0:8000`

### 2. Send Request from Postman

- Use Postman collection (see `doc/guides/api-testing.md`)
- Send request to trigger breakpoint
- PyCharm pauses execution

### 3. Inspect Variables

**Key variables to check:**
- `ctx` - RequestContext (trace_id, request_id)
- `request` - Request payload
- `order_data` - Order details
- `slices` - Generated order slices

**Use Variables panel:**
- Bottom of debug window
- Expand objects to see fields
- Right-click → "Evaluate Expression" for complex checks

### 4. Step Through Code

- **Step Over (F8)** - Execute current line
- **Step Into (F7)** - Go into function calls
- **Step Out (Shift+F8)** - Return to caller
- **Resume (F9)** - Continue to next breakpoint

### 5. Evaluate Expressions

**Debug Console:**
- Bottom panel → "Console" tab
- Type Python expressions
- Check values, call functions

**Examples:**
```python
# Check context
ctx.to_dict()

# Check order status
order['order_queue_status']

# Count slices
len(slices)
```

---

## Common Debugging Scenarios

### Scenario 1: Order Not Being Created

**Breakpoints:**
1. `gapi/api/routes.py` - GAPI endpoint
2. `pulse/api/routes.py` - Pulse endpoint
3. `pulse/repositories/order_repository.py` - Database insert

**Check:**
- Request validation
- Auth token
- Database connection
- Constraint violations

### Scenario 2: Background Worker Not Processing

**Breakpoints:**
1. `pulse/workers/splitting_worker.py` - Worker loop
2. `pulse/repositories/order_repository.py` - Get pending orders
3. `pulse/services/splitting_service.py` - Split logic

**Check:**
- Worker is running
- Orders in PENDING status
- Database query results
- Processing errors

### Scenario 3: Order Slices Not Created

**Breakpoints:**
1. `pulse/services/splitting_service.py` - Split calculation
2. `pulse/repositories/order_slice_repository.py` - Slice creation

**Check:**
- Split configuration (num_splits, time_window)
- Slice generation logic
- Database insert
- Transaction commit

### Scenario 4: Tracing Not Working

**Breakpoints:**
1. `shared/middleware/context.py` - Context creation
2. `pulse/repositories/order_repository.py` - Database write with context

**Check:**
- Headers in request
- Context object fields
- Database columns (trace_id, request_id)
- Log output

---

## Environment Variables for Debugging

Create `.env.debug` for debug-specific settings:

```bash
# Enable debug logging
LOG_LEVEL=DEBUG

# Disable background workers (debug API only)
WORKERS_ENABLED=false

# Use mock broker
ZERODHA_USE_MOCK=true
ZERODHA_MOCK_SCENARIO=success

# Database
PULSE_DB_HOST=localhost
PULSE_DB_PORT=5432
PULSE_DB_NAME=pulse_dev
```

Load in debug configuration:
```xml
<option name="PARAMETERS" value="--env-file .env.debug" />
```

---

## Tips

### Conditional Breakpoints

Right-click breakpoint → **Edit Breakpoint** → Add condition:
```python
order_id == "ord_specific_id"
```

### Log Points

Right-click breakpoint → **More** → Check "Evaluate and log":
```python
f"Order status: {order['order_queue_status']}"
```

### Watch Expressions

Add expressions to watch continuously:
- Right-click variable → **Add to Watches**
- Or manually add in Watches panel

---

## See Also

- **Standard:** [IDE Setup Standard](../../contracts/standards/ide-setup/README.md)
- **API Testing:** `doc/guides/api-testing.md`
- **Logging:** `contracts/standards/logging/README.md`
- **Tracing:** `contracts/standards/tracing/README.md`

