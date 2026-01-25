# Testing Standard

## Purpose

Define standards for unit tests and integration tests to ensure code quality, reliability, and maintainability.

---

## Test Categories

### Unit Tests
- Test individual functions, classes, or modules in isolation
- Mock external dependencies (databases, HTTP calls, file I/O)
- Fast execution (milliseconds per test)
- No network or database access
- Located in `tests/unit/`

### Integration Tests
- Test interaction between components or services
- May use real dependencies (test database, HTTP server)
- Slower execution (seconds per test)
- Test end-to-end flows
- Located in `tests/integration/`

---

## Directory Structure

Tests are organized at the root level, mirroring the project structure:

```
tests/
├── unit/                           # Fast, isolated tests
│   ├── services/
│   │   ├── gapi/
│   │   │   ├── test_health.py
│   │   │   └── test_hello.py
│   │   └── order_service/
│   │       ├── test_health.py
│   │       └── test_hello.py
│   └── shared/
│       ├── observability/
│       │   ├── test_context.py
│       │   ├── test_logger.py
│       │   └── test_middleware.py
│       └── http/
│           └── test_client.py
└── integration/                    # End-to-end tests
    ├── services/
    │   ├── gapi/
    │   │   └── test_api_endpoints.py
    │   └── order_service/
    │       └── test_api_endpoints.py
    └── shared/
        └── observability/
            └── test_context_propagation.py
```

### Principles

1. **Mirror project structure** - Test paths mirror source code paths
   - `shared/observability/context.py` → `tests/unit/shared/observability/test_context.py`
   - `services/gapi/main.py` → `tests/unit/services/gapi/test_main.py`

2. **Organize by test type first** - Unit vs Integration
   - `tests/unit/` - Fast, isolated, no external dependencies
   - `tests/integration/` - End-to-end, may use real dependencies

3. **Support shared code testing** - Shared modules have their own tests
   - Service tests in `tests/*/services/`
   - Shared tests in `tests/*/shared/`

---

## Naming Conventions

### Test Files
- Prefix with `test_`: `test_orders.py`, `test_validation.py`
- Mirror the structure of source code
- One test file per source module

### Test Functions
- Prefix with `test_`: `test_create_order_success()`
- Descriptive names: `test_validation_fails_when_quantity_negative()`
- Use underscores for readability

### Test Classes (Optional)
- Prefix with `Test`: `TestOrderCreation`
- Group related tests together

---

## Test Structure (AAA Pattern)

Every test should follow the **Arrange-Act-Assert** pattern:

```python
def test_create_order_success():
    # Arrange: Set up test data and mocks
    order_data = {"instrument": "NSE:RELIANCE", "quantity": 10}
    
    # Act: Execute the function under test
    result = create_order(order_data)
    
    # Assert: Verify the outcome
    assert result["status"] == "success"
    assert result["order_id"] is not None
```

---

## Unit Test Requirements

### 1. Isolation
- Mock all external dependencies
- Use `unittest.mock` or `pytest-mock`
- No real HTTP calls, database queries, or file I/O

### 2. Coverage
Every unit test MUST cover:
- **Success path**: Normal operation with valid inputs
- **Validation failures**: Invalid inputs, missing fields
- **Edge cases**: Empty values, boundary conditions, null values

### 3. Example: Unit Test

```python
from unittest.mock import Mock, patch
import pytest

def test_health_endpoint_returns_ok():
    # Arrange
    # (no setup needed for simple endpoint)
    
    # Act
    response = health()
    
    # Assert
    assert response == {"status": "ok"}


def test_create_order_validates_quantity():
    # Arrange
    invalid_order = {"instrument": "NSE:RELIANCE", "quantity": -5}
    
    # Act & Assert
    with pytest.raises(ValidationError) as exc:
        create_order(invalid_order)
    
    assert "quantity" in str(exc.value)


@patch('services.order_service.repository.save_order')
def test_create_order_calls_repository(mock_save):
    # Arrange
    order_data = {"instrument": "NSE:RELIANCE", "quantity": 10}
    mock_save.return_value = {"order_id": "o-123"}
    
    # Act
    result = create_order(order_data)
    
    # Assert
    mock_save.assert_called_once()
    assert result["order_id"] == "o-123"
```

---

## Integration Test Requirements

### 1. Real Dependencies
- Use TestClient for FastAPI endpoints
- May use in-memory database or test database
- Test actual HTTP requests/responses

### 2. Coverage
Every integration test MUST cover:
- **Success path**: Complete end-to-end flow
- **Authentication**: Auth failures (if applicable)
- **Error handling**: Service errors, timeouts

### 3. Example: Integration Test

```python
from fastapi.testclient import TestClient
from services.gapi.main import app

client = TestClient(app)


def test_health_endpoint():
    # Act
    response = client.get("/health")
    
    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_hello_endpoint_returns_message():
    # Act
    response = client.get("/api/hello")
    
    # Assert
    assert response.status_code == 200
    assert "message" in response.json()
    assert response.json()["message"] == "Hello from GAPI"


def test_hello_endpoint_includes_tracing_headers():
    # Arrange
    headers = {
        "X-Request-Id": "r-test123",
        "X-Trace-Id": "t-test456"
    }
    
    # Act
    response = client.get("/api/hello", headers=headers)
    
    # Assert
    assert response.status_code == 200
    assert response.headers["X-Request-Id"] == "r-test123"
    assert response.headers["X-Trace-Id"] == "t-test456"
```

---

## Test Data

### Fixtures (pytest)
Use fixtures for reusable test data:

```python
import pytest

@pytest.fixture
def valid_order():
    return {
        "instrument": "NSE:RELIANCE",
        "quantity": 10,
        "action": "BUY"
    }

@pytest.fixture
def mock_logger():
    return Mock()

def test_with_fixture(valid_order):
    result = validate_order(valid_order)
    assert result is True
```

### Test Data Files
- Store in `tests/fixtures/` directory
- Use JSON or YAML for complex data
- Keep test data minimal and focused

---

## Assertions

### Good Assertions
```python
# Specific and clear
assert response.status_code == 200
assert result["order_id"].startswith("o-")
assert len(errors) == 2

# Multiple assertions for complex objects
assert response["status"] == "success"
assert response["data"]["instrument"] == "NSE:RELIANCE"
```

### Avoid
```python
# Too vague
assert response  # What are we checking?
assert result is not None  # Not specific enough

# Testing implementation details
assert mock.call_count == 1  # Fragile
```

---

## Running Tests

### Run All Tests
```bash
python -m pytest -v
```

### Run Unit Tests Only
```bash
python -m pytest tests/unit/ -v
```

### Run Integration Tests Only
```bash
python -m pytest tests/integration/ -v
```

### Run Specific Service Tests
```bash
# GAPI unit tests
python -m pytest tests/unit/services/gapi/ -v

# Order Service integration tests
python -m pytest tests/integration/services/order_service/ -v
```

### Run Shared Module Tests
```bash
# All shared unit tests
python -m pytest tests/unit/shared/ -v

# Specific shared module
python -m pytest tests/unit/shared/observability/ -v
```

### Run with Coverage
```bash
python -m pytest --cov=services --cov=shared --cov-report=html
```

### Run Specific Test
```bash
python -m pytest tests/unit/services/gapi/test_health.py::test_health_returns_ok -v
```

---

## Test Requirements (Mandatory)

1. **Every new endpoint MUST have tests**
   - At least one integration test for success path
   - Unit tests for business logic

2. **Every test MUST be independent**
   - No shared state between tests
   - Tests can run in any order

3. **Tests MUST be fast**
   - Unit tests: < 100ms each
   - Integration tests: < 5s each

4. **Tests MUST be deterministic**
   - No random data without seeding
   - No time-dependent assertions without mocking

5. **Tests MUST clean up**
   - Reset mocks after each test
   - Clear test data from databases

---

## CI/CD Integration

Tests run automatically on:
- Every commit
- Every pull request
- Before deployment

**Build fails if:**
- Any test fails
- Coverage drops below threshold (TBD)
- Tests take too long (timeout)

---

## Tools

- **Test Framework**: pytest
- **Mocking**: unittest.mock (standard library)
- **HTTP Testing**: FastAPI TestClient
- **Coverage**: pytest-cov

---

## Anti-Patterns (Avoid)

❌ **Don't disable tests to make builds pass**
❌ **Don't test implementation details**
❌ **Don't write tests that depend on external services**
❌ **Don't use sleep() for timing - use mocks**
❌ **Don't share state between tests**
❌ **Don't write tests without assertions**

---

## Relationship to Other Standards

- Error codes defined in `contracts/schemas/common.md`
- Logging format in `doc/guides/logging.md`
- Tracing headers in `doc/guides/tracing.md`

