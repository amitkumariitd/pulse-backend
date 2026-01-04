# Postman Collection for Pulse Backend

This directory contains Postman collections and environments for testing the Pulse Backend API.

## Files

- **`pulse-backend.postman_collection.json`** - Main API collection with all endpoints
- **`local.postman_environment.json`** - Local development environment variables

## Quick Start

### 1. Import Collection into Postman

**Option A: Import from File**
1. Open Postman
2. Click **Import** button (top left)
3. Click **Upload Files**
4. Select `pulse-backend.postman_collection.json`
5. Click **Import**

**Option B: Import from Folder**
1. Open Postman
2. Click **Import** → **Folder**
3. Select the `postman/` directory
4. Postman will import both collection and environment

### 2. Import Environment

1. Click **Import** button
2. Select `local.postman_environment.json`
3. Click **Import**
4. Select **"Pulse Backend - Local"** from environment dropdown (top right)

### 3. Start the Application

```bash
# Make sure PostgreSQL is running
# Then start the app
uvicorn main:app --reload --port 8000
```

### 4. Test the APIs

**Health Check:**
- Request: `GET /health`
- No auth required
- Should return: `{"status":"ok","background_workers":"running"}`

**Create Order (GAPI):**
- Request: `POST /gapi/api/orders`
- Requires: `Authorization: Bearer test-token-123`
- Body: See collection for example
- Returns: `order_id` - **Copy this for next requests**

**Get Order:**
- Request: `GET /pulse/internal/orders/{{order_id}}`
- Set `order_id` variable to the ID from previous step
- Returns: Full order details

**Get Order Slices:**
- Request: `GET /pulse/internal/orders/{{order_id}}/slices`
- Returns: Array of slices created for the order

## Collection Variables

The collection uses these variables (can be overridden by environment):

- **`base_url`** - API base URL (default: `http://localhost:8000`)
- **`auth_token`** - Authentication token for GAPI (default: `test-token-123`)
- **`order_id`** - Order ID for testing (set manually after creating an order)

## Setting the Order ID Variable

After creating an order, you'll get an `order_id` in the response. To use it in subsequent requests:

**Option 1: Manual**
1. Copy the `order_id` from response
2. Click **Environments** (top right)
3. Select **"Pulse Backend - Local"**
4. Paste value into `order_id` field
5. Save

**Option 2: Automatic (using Tests)**
The collection can auto-save `order_id` from responses. Add this to the **Tests** tab of "Create Order" request:

```javascript
// Auto-save order_id from response
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("order_id", response.order_id);
    console.log("Saved order_id:", response.order_id);
}
```

## API Endpoints

### Health
- `GET /health` - Check application health

### GAPI (External API)
- `POST /gapi/api/orders` - Create order (requires auth)

### Pulse API (Internal)
- `POST /pulse/internal/orders` - Create order (internal, no auth)
- `GET /pulse/internal/orders/{order_id}` - Get order details
- `GET /pulse/internal/orders/{order_id}/slices` - Get order slices

## Example Workflow

1. **Start app**: `uvicorn main:app --reload --port 8000`
2. **Health check**: Run "Health Check" request → Should return OK
3. **Create order**: Run "Create Order" request → Copy `order_id` from response
4. **Set variable**: Paste `order_id` into environment variable
5. **Wait 5-10 seconds**: Background worker will split the order
6. **Get order**: Run "Get Order by ID" → Should show `order_queue_status: "COMPLETED"`
7. **Get slices**: Run "Get Order Slices" → Should show 5 slices (or whatever `num_splits` you used)

## Troubleshooting

### "Could not get response"
- Check if the app is running: `curl http://localhost:8000/health`
- Check the port matches `base_url` in environment

### "Unauthorized" error
- Make sure you're using the "Create Order" request under **GAPI** folder
- Check `Authorization` header is set to `Bearer {{auth_token}}`
- Verify environment is selected (top right dropdown)

### "Order not found"
- Make sure you've set the `order_id` variable
- Check the order was created successfully
- Verify you're using the correct `order_id`

## Adding More Environments

To add staging/production environments:

1. Duplicate `local.postman_environment.json`
2. Rename to `staging.postman_environment.json`
3. Update `base_url` and `auth_token` values
4. Import into Postman

Example staging environment:
```json
{
  "name": "Pulse Backend - Staging",
  "values": [
    {
      "key": "base_url",
      "value": "https://staging.pulse.example.com",
      "enabled": true
    },
    {
      "key": "auth_token",
      "value": "staging-token-xyz",
      "enabled": true
    }
  ]
}
```

## Version Control

These files are checked into git so the whole team can use them:
- ✅ Collection file (`.postman_collection.json`)
- ✅ Environment files (`.postman_environment.json`)
- ❌ Don't commit files with real credentials/tokens

For production credentials, use Postman's secret variables or environment variables that are not committed.

## Keeping Collection Updated

When you add new endpoints:
1. Add them in Postman
2. Export the collection: Right-click → Export → Collection v2.1
3. Save to `postman/pulse-backend.postman_collection.json`
4. Commit the changes to git

This keeps the collection in sync with the codebase.

