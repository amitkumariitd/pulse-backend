# Postman Setup Guide

Quick guide to using Postman with Pulse Backend.

## Import Collection

### Method 1: Import Files (Recommended)

```bash
# 1. Open Postman
# 2. Click "Import" button (top left)
# 3. Click "Upload Files"
# 4. Navigate to pulse-backend/postman/
# 5. Select both files:
#    - pulse-backend.postman_collection.json
#    - local.postman_environment.json
# 6. Click "Import"
```

### Method 2: Import Folder

```bash
# 1. Open Postman
# 2. Click "Import" → "Folder"
# 3. Select the pulse-backend/postman/ directory
# 4. Click "Import"
```

## Select Environment

1. Look at top-right corner of Postman
2. Click environment dropdown
3. Select **"Pulse Backend - Local"**
4. You should see: `base_url: http://localhost:8000`

## Test the APIs

### 1. Start the Application

```bash
# Make sure PostgreSQL is running
# Then start the app
uvicorn main:app --reload --port 8000
```

### 2. Run Health Check

- Open **"Health"** folder in collection
- Click **"Health Check"**
- Click **"Send"**
- Should return: `{"status":"ok","background_workers":"running"}`

### 3. Create an Order

- Open **"GAPI (External API)"** folder
- Click **"Create Order"**
- Click **"Send"**
- Copy the `order_id` from response (e.g., `"ord_1234567890abcdef"`)

### 4. Set Order ID Variable

**Option A: Manual**
1. Click **Environments** icon (top right)
2. Click **"Pulse Backend - Local"**
3. Find `order_id` row
4. Paste the order ID in **CURRENT VALUE** column
5. Click **Save** (Cmd+S)

**Option B: Automatic (Recommended)**
1. Click **"Create Order"** request
2. Go to **"Tests"** tab
3. Add this script:
```javascript
if (pm.response.code === 200) {
    const response = pm.response.json();
    pm.environment.set("order_id", response.order_id);
    console.log("Saved order_id:", response.order_id);
}
```
4. Save the request
5. Now every time you create an order, `order_id` is auto-saved

### 5. Get Order Details

- Wait 5-10 seconds (for background worker to process)
- Open **"Pulse API (Internal)"** folder
- Click **"Get Order by ID"**
- Click **"Send"**
- Should show order with `order_queue_status: "COMPLETED"`

### 6. Get Order Slices

- Click **"Get Order Slices"**
- Click **"Send"**
- Should return array of 5 slices (or whatever `num_splits` you used)

## Available Endpoints

### Health
- `GET /health` - Check application health

### GAPI (External API)
- `POST /gapi/api/orders` - Create order (requires auth)
  - Header: `Authorization: Bearer test-token-123`

### Pulse API (Internal)
- `POST /pulse/internal/orders` - Create order (internal, no auth)
- `GET /pulse/internal/orders/{order_id}` - Get order details
- `GET /pulse/internal/orders/{order_id}/slices` - Get order slices

## Variables

The collection uses these variables:

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `base_url` | `http://localhost:8000` | API base URL |
| `auth_token` | `test-token-123` | GAPI authentication token |
| `order_id` | (empty) | Order ID for testing (set after creating order) |

## Troubleshooting

### "Could not get response"
```bash
# Check if app is running
curl http://localhost:8000/health

# If not, start it
uvicorn main:app --reload --port 8000
```

### "Unauthorized" error
- Make sure you're using requests under **"GAPI (External API)"** folder
- Check that `Authorization` header is present
- Verify environment is selected (top-right dropdown)

### "Order not found"
- Make sure you've set the `order_id` variable
- Check you copied the correct order ID
- Verify the order was created successfully

### Variables not working
- Check environment is selected: **"Pulse Backend - Local"** (top-right)
- Variables use double curly braces: `{{variable_name}}`
- Check variable spelling matches exactly

## Adding Production Environment

When you have a production/staging server:

1. Duplicate `postman/local.postman_environment.json`
2. Rename to `postman/production.postman_environment.json`
3. Update values:
```json
{
  "name": "Pulse Backend - Production",
  "values": [
    {
      "key": "base_url",
      "value": "https://api.pulse.example.com",
      "enabled": true
    },
    {
      "key": "auth_token",
      "value": "{{PRODUCTION_TOKEN}}",
      "enabled": true
    }
  ]
}
```
4. **DO NOT commit real production credentials to git**
5. Use Postman's secret variables or local-only environment files

## Keeping Collection Updated

When you add new endpoints:

1. Add them in Postman
2. Test them
3. Export collection:
   - Right-click collection → **Export**
   - Choose **Collection v2.1**
   - Save to `postman/pulse-backend.postman_collection.json`
4. Commit to git:
```bash
git add postman/
git commit -m "docs: update Postman collection with new endpoints"
```

This keeps the collection in sync with the codebase for the whole team.

## See Also

- Full documentation: `postman/README.md`
- API contracts: `doc/contract/`
- Local setup: `doc/guides/local-setup.md`

