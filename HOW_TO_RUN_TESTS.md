# How to Run Tests

## ✅ All Tests Passing (20/20)

```bash
python -m pytest -v
```

**Result:**
- GAPI: 10 tests ✅
- Order Service: 10 tests ✅
- **Total: 20 tests passing**

---

## Quick Commands

### Run All Tests
```bash
# Simple
pytest

# With verbose output
pytest -v

# Using Python module (recommended)
python -m pytest -v
```

### Run Specific Service Tests
```bash
# GAPI only
pytest services/gapi/tests/

# Order Service only
pytest services/order_service/tests/
```

### Run by Test Type
```bash
# Unit tests only (fast)
pytest services/gapi/tests/unit/
pytest services/order_service/tests/unit/

# Integration tests only
pytest services/gapi/tests/integration/
pytest services/order_service/tests/integration/
```

### Run Specific Test File
```bash
pytest services/gapi/tests/unit/test_health.py
```

### Run Specific Test Function
```bash
pytest services/gapi/tests/unit/test_health.py::test_health_returns_ok
```

### Run with Coverage
```bash
# Generate coverage report
pytest --cov=services --cov-report=html

# View report (macOS)
open htmlcov/index.html

# Terminal report
pytest --cov=services --cov-report=term
```

---

## Test Structure

```
services/
├── gapi/
│   └── tests/
│       ├── unit/              # Fast, isolated tests
│       │   ├── test_health.py
│       │   └── test_hello.py
│       └── integration/       # End-to-end tests
│           └── test_api_endpoints.py
└── order_service/
    └── tests/
        ├── unit/
        │   ├── test_health.py
        │   └── test_hello.py
        └── integration/
            └── test_api_endpoints.py
```

---

## Current Test Coverage

### GAPI (10 tests)
**Unit Tests (4):**
- `test_health_returns_ok` - Health endpoint returns correct status
- `test_health_logs_request` - Health endpoint logs correctly
- `test_hello_returns_message` - Hello endpoint returns message
- `test_hello_logs_with_data` - Hello endpoint logs with data

**Integration Tests (6):**
- `test_health_endpoint_success` - Health endpoint HTTP success
- `test_health_endpoint_includes_tracing_headers` - Tracing headers in response
- `test_health_endpoint_generates_tracing_headers_when_missing` - Auto-generate headers
- `test_hello_endpoint_success` - Hello endpoint HTTP success
- `test_hello_endpoint_includes_tracing_headers` - Tracing headers in response
- `test_hello_endpoint_content_type` - Correct content type

### Order Service (10 tests)
Same structure as GAPI

---

## Troubleshooting

### Import Errors
If you see import errors, make sure you're running from the repository root:

```bash
cd /Users/amitkumar/learn/pulse-backend
python -m pytest -v
```

### Module Not Found
Make sure dependencies are installed:

```bash
pip install -r requirements.txt
```

### Tests Not Discovered
Check that pytest.ini is configured correctly:

```ini
[pytest]
testpaths = services
python_files = test_*.py
```

---

## Next Steps

To add context to endpoints:

```python
from fastapi import Depends
from shared.observability.dependencies import get_context
from shared.observability.context import RequestContext

@app.get("/api/orders")
async def list_orders(ctx: RequestContext = Depends(get_context)):
    logger.info("Listing orders", ctx)
    return {"orders": []}
```

---

## See Also

- **TESTING.md** - Detailed testing guide
- **doc/standards/testing.md** - Testing standards
- **doc/standards/context.md** - Context standard

