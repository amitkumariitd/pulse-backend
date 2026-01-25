# PyCharm Debug Setup

Guide to running Pulse Backend in debug mode with PyCharm.

---

## Quick Start

### 1. Open Project in PyCharm

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

### 3. Use the Debug Configuration

The debug configuration is already created at `.idea/runConfigurations/Pulse_Backend_Debug.xml`

1. Look at top-right corner of PyCharm
2. Select **"Pulse Backend - Debug"** from dropdown
3. Click the **Debug** button (bug icon) or press **Ctrl+D**

---

## Setting Breakpoints

### Add Breakpoints

1. Open any Python file (e.g., `pulse/api/routes.py`)
2. Click in the **left gutter** (next to line numbers)
3. A **red dot** appears = breakpoint set

### Example Breakpoints to Try

**API Endpoint:**
```python
# File: pulse/api/routes.py
@router.post("/internal/orders")
async def create_order(request: CreateOrderRequest, ctx: RequestContext = Depends(get_request_context)):
    # Set breakpoint here ← Click in gutter
    logger.info(f"Creating order: {request.instrument}")
```

**Background Worker:**
```python
# File: pulse/workers/splitting_worker.py
async def process_pending_orders(self):
    # Set breakpoint here ← Click in gutter
    logger.info("Splitting worker: Checking for pending orders")
```

**Repository:**
```python
# File: pulse/repositories/order_repository.py
async def create_order(self, order_data: dict, ctx: RequestContext) -> dict:
    # Set breakpoint here ← Click in gutter
    conn = await self.get_connection()
```

---

## Debug Workflow

### 1. Start Debug Mode

- Click **Debug** button (bug icon) or **Ctrl+D**
- Wait for app to start
- Console shows: `Uvicorn running on http://0.0.0.0:8000`

### 2. Send Request from Postman

```
POST http://localhost:8000/gapi/api/orders

Headers:
Authorization: Bearer test-token-123
Content-Type: application/json

Body:
{
  "instrument": "NSE:RELIANCE",
  "side": "BUY",
  "total_quantity": 100,
  "num_splits": 5,
  "duration_minutes": 60,
  "randomize": true
}
```

### 3. Hit Breakpoint

- PyCharm **pauses execution** at your breakpoint
- **Debugger panel** opens at bottom
- You can now:
  - **Inspect variables** (hover over them or check Variables panel)
  - **Step through code** (F8 = step over, F7 = step into)
  - **Evaluate expressions** (Alt+F8)
  - **View call stack**

### 4. Debug Controls

| Action | Shortcut | Description |
|--------|----------|-------------|
| **Resume** | F9 | Continue execution |
| **Step Over** | F8 | Execute current line, don't go into functions |
| **Step Into** | F7 | Go into function calls |
| **Step Out** | Shift+F8 | Exit current function |
| **Evaluate** | Alt+F8 | Evaluate any expression |
| **Stop** | Cmd+F2 | Stop debugging |

---

## Debugging Background Workers

Background workers run in separate asyncio tasks. To debug them:

### 1. Set Breakpoint in Worker

```python
# File: pulse/workers/splitting_worker.py
async def run(self):
    while True:
        try:
            # Set breakpoint here ← Will hit every 5 seconds
            await self.process_pending_orders()
            await asyncio.sleep(5)
```

### 2. Wait for Worker to Run

- Workers run automatically when app starts
- Splitting worker runs every **5 seconds**
- Timeout monitor runs every **60 seconds**
- Breakpoint will hit when worker executes

### 3. Inspect Worker State

When breakpoint hits, you can inspect:
- `self.pool` - Database connection pool
- `pending_orders` - Orders being processed
- `ctx` - Request context with trace_id

---

## Debugging Database Queries

### Set Breakpoint in Repository

```python
# File: pulse/repositories/order_repository.py
async def get_pending_orders(self, ctx: RequestContext) -> list[dict]:
    conn = await self.get_connection()
    try:
        # Set breakpoint here ← Inspect SQL query
        query = """
            SELECT * FROM orders 
            WHERE order_queue_status = 'PENDING'
            ORDER BY created_at ASC
        """
        rows = await conn.fetch(query)
        # Set breakpoint here ← Inspect results
        return [dict(row) for row in rows]
```

### Inspect Variables

- **conn** - Database connection object
- **query** - SQL query string
- **rows** - Query results
- **ctx.trace_id** - Current trace ID

---

## Debugging with Postman

### Workflow

1. **Start debug mode** in PyCharm
2. **Set breakpoints** in your code
3. **Send request** from Postman
4. **PyCharm pauses** at breakpoint
5. **Inspect variables**, step through code
6. **Resume** (F9) to continue
7. **Postman receives response**

### Example: Debug Order Creation

**Breakpoints to set:**
1. `gapi/api/routes.py` - Line where order is received
2. `pulse/api/routes.py` - Line where order is created
3. `pulse/repositories/order_repository.py` - Line where order is inserted
4. `pulse/workers/splitting_worker.py` - Line where order is split

**Send request from Postman** → Watch execution flow through all layers!

---

## Tips & Tricks

### Conditional Breakpoints

Right-click breakpoint → **Edit Breakpoint** → Add condition:
```python
# Only break when instrument is RELIANCE
request.instrument == "NSE:RELIANCE"

# Only break for specific order
order_data['id'] == 'ord_abc123'
```

### Evaluate Expressions

When paused at breakpoint:
1. Press **Alt+F8**
2. Type any Python expression:
   ```python
   order_data['total_quantity'] / order_data['num_splits']
   ctx.trace_id
   len(pending_orders)
   ```
3. See result instantly

### Watch Variables

Right-click variable → **Add to Watches**
- Variable value updates as you step through code
- Useful for tracking state changes

### Debug Console

When paused, use **Debug Console** tab:
```python
# Execute any Python code
print(order_data)
dir(ctx)
await conn.fetchval("SELECT COUNT(*) FROM orders")
```

---

## Troubleshooting

### Breakpoints Not Hitting

**Problem:** Breakpoint is gray/hollow, not red
**Solution:** 
- Make sure debug mode is running (not normal run)
- Check Python interpreter is set to `.venv/bin/python`
- Restart debug session

### "Module not found" Error

**Problem:** `ModuleNotFoundError: No module named 'pulse'`
**Solution:**
- Check **Working Directory** is set to project root
- Verify Python interpreter is using `.venv`
- Mark `pulse-backend` as **Sources Root** (right-click folder)

### Auto-reload Breaks Debugging

**Problem:** Code changes cause debugger to disconnect
**Solution:**
- Use **"Pulse Backend - Debug (No Reload)"** configuration
- Or manually restart debug session after code changes

### Background Workers Not Stopping

**Problem:** Workers keep running after stopping debugger
**Solution:**
- Use **Cmd+F2** to force stop
- Or restart PyCharm

---

## Alternative: Manual Debug Configuration

If the auto-created configuration doesn't work, create manually:

### 1. Edit Configurations

1. Top-right → **Edit Configurations**
2. Click **+** → **Python**
3. Name: `Pulse Backend - Debug`

### 2. Configure Settings

```
Script path: (leave empty)
Module name: uvicorn
Parameters: main:app --reload --port 8000 --log-level debug
Python interpreter: .venv/bin/python
Working directory: /Users/amitkumar/learn/pulse-backend
Environment variables: LOG_LEVEL=DEBUG
```

### 3. Save and Run

- Click **OK**
- Select configuration from dropdown
- Click **Debug** button

---

## See Also

- **Postman Setup:** `doc/guides/postman-setup.md`
- **Testing Guide:** `contracts/standards/testing/README.md`
- **Logging Guide:** `contracts/standards/logging/README.md`

