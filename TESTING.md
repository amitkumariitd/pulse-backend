# Testing Guide

> **Mandatory Rule**: Every code change MUST have tests. See `.augment/rules/rules.md` for enforcement policy.

## Quick Start

```bash
# Run all tests
python -m pytest -v

# With coverage
python -m pytest --cov=services --cov=shared --cov-report=html
open htmlcov/index.html
```

**Status**: 40/40 tests passing ✅

---

## Run Specific Tests

```bash
# By test type
python -m pytest tests/unit/ -v          # All unit tests (8 tests)
python -m pytest tests/integration/ -v   # All integration tests (12 tests)

# By service
python -m pytest tests/unit/services/gapi/ -v
python -m pytest tests/unit/services/order_service/ -v
python -m pytest tests/integration/services/gapi/ -v
python -m pytest tests/integration/services/order_service/ -v

# Shared modules
python -m pytest tests/unit/shared/ -v
python -m pytest tests/integration/shared/ -v

# Specific file
python -m pytest tests/unit/services/gapi/test_health.py -v

# Specific function
python -m pytest tests/unit/services/gapi/test_health.py::test_health_returns_ok -v
```

---

## Test Structure

```
tests/
├── unit/                           # Fast, isolated tests (22 tests)
│   ├── services/
│   │   ├── gapi/                   # GAPI unit tests (4 tests)
│   │   └── order_service/          # Order Service unit tests (4 tests)
│   └── shared/
│       ├── observability/          # Context, logger, middleware tests (14 tests)
│       └── http/                   # HTTP client tests
└── integration/                    # End-to-end tests (18 tests)
    ├── services/
    │   ├── gapi/                   # GAPI integration tests (9 tests)
    │   └── order_service/          # Order Service integration tests (9 tests)
    └── shared/
        └── observability/          # Cross-service integration tests
```

**Total**: 40 tests, 100% passing

### Key Principles
- **Mirrors project structure** - `shared/observability/context.py` → `tests/unit/shared/observability/test_context.py`
- **Organized by type** - Unit tests in `tests/unit/`, integration tests in `tests/integration/`
- **Supports shared code** - Shared modules have their own tests in `tests/*/shared/`

---

## Writing New Tests

### What Requires Tests

**Every code change MUST have tests:**

- **New endpoints** → integration tests covering:
  - ✅ Success path
  - ✅ Validation failure
  - ✅ Auth failure (if applicable)
  - ✅ Tracing headers

- **New functions/methods** → unit tests covering:
  - ✅ Expected behavior
  - ✅ Edge cases
  - ✅ Error conditions

- **Modified behavior** → regression tests:
  - ✅ New behavior works
  - ✅ Existing behavior still works
  - ✅ Edge cases handled

- **Middleware changes** → tests for:
  - ✅ Request/response handling
  - ✅ Header manipulation
  - ✅ Context creation/propagation

- **Shared utilities** → comprehensive tests:
  - ✅ All public functions
  - ✅ Validation logic
  - ✅ Format/parsing logic

### AAA Pattern

```python
def test_example():
    # Arrange
    data = {"key": "value"}

    # Act
    result = my_function(data)

    # Assert
    assert result["status"] == "success"
```

### Test Requirements

- Tests MUST be written BEFORE marking work as complete
- Tests MUST pass before considering the change done
- Tests MUST verify actual behavior, not just call the code
- Do NOT disable tests to make builds pass
- Do NOT skip tests because "it's simple" or "obvious"

---

## Troubleshooting

**`pytest` command not found?** Use `python -m pytest` instead:
```bash
python -m pytest -v
```

**Import errors?** Make sure you're in the repo root:
```bash
cd /Users/amitkumar/learn/pulse-backend
python -m pytest -v
```

**Missing dependencies?**
```bash
pip install -r requirements.txt
```

---

## See Also

- [Testing Standard](doc/standards/testing.md)
- [Context Standard](doc/standards/context.md)

