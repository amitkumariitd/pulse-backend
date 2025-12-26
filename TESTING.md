# Testing Guide

## Quick Start

### Run All Tests
```bash
pytest
```

### Run Unit Tests Only
```bash
pytest services/gapi/tests/unit/
pytest services/order_service/tests/unit/
```

### Run Integration Tests Only
```bash
pytest services/gapi/tests/integration/
pytest services/order_service/tests/integration/
```

### Run with Coverage
```bash
pytest --cov=services --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Specific Test
```bash
pytest services/gapi/tests/unit/test_health.py::test_health_returns_ok
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

**GAPI**: 100% coverage
- 4 unit tests
- 6 integration tests

**Order Service**: 100% coverage
- 4 unit tests
- 6 integration tests

**Total**: 20 tests, all passing ✅

---

## Test Categories

### Unit Tests
- Test individual functions in isolation
- Mock external dependencies
- Fast execution (< 100ms each)
- Located in `tests/unit/`

### Integration Tests
- Test complete HTTP request/response flow
- Use FastAPI TestClient
- Test tracing headers propagation
- Located in `tests/integration/`

---

## Writing New Tests

### 1. Create Test File
Follow naming convention: `test_<module>.py`

### 2. Use AAA Pattern
```python
def test_example():
    # Arrange: Set up test data
    data = {"key": "value"}
    
    # Act: Execute the function
    result = my_function(data)
    
    # Assert: Verify the outcome
    assert result["status"] == "success"
```

### 3. Test Coverage Requirements
Every new endpoint MUST have:
- ✅ Success path test
- ✅ Validation failure test (if applicable)
- ✅ Tracing headers test

---

## CI/CD

Tests run automatically on:
- Every commit
- Every pull request
- Before deployment

Build fails if any test fails.

---

## See Also

- [Testing Standard](doc/standards/testing.md) - Detailed testing guidelines
- [Logging Standard](doc/standards/logging.md) - Logging format and requirements
- [Tracing Standard](doc/standards/tracing.md) - Distributed tracing model

