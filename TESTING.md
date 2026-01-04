# Testing Guide

> **Mandatory Rule**: Every code change MUST have tests. See `.augment/rules/rules.md` for enforcement policy.

## Quick Start

```bash
# Run all tests
python -m pytest -v

# With coverage
python -m pytest --cov=gapi --cov=pulse --cov=shared --cov-report=html
open htmlcov/index.html
```

**Status**: 116/120 tests passing (4 pre-existing failures in timeout_monitor tests)

---

## Run Specific Tests

```bash
# By test type
python -m pytest tests/unit/ -v          # All unit tests (80 tests)
python -m pytest tests/integration/ -v   # All integration tests (40 tests)

# By component
python -m pytest tests/unit/services/gapi/ -v
python -m pytest tests/unit/services/pulse/ -v
python -m pytest tests/integration/services/gapi/ -v
python -m pytest tests/integration/services/pulse/ -v

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
├── unit/                           # Fast, isolated tests (80 tests)
│   ├── repositories/               # Repository tests (12 tests)
│   ├── services/
│   │   ├── gapi/                   # GAPI unit tests (10 tests)
│   │   └── pulse/                  # Pulse unit tests (16 tests)
│   └── shared/
│       ├── observability/          # Context, logger, middleware tests (39 tests)
│       └── http/                   # HTTP client tests (3 tests)
└── integration/                    # End-to-end tests (40 tests)
    ├── database/                   # Database pool tests (4 tests)
    ├── services/
    │   ├── gapi/                   # GAPI integration tests (14 tests)
    │   └── pulse/                  # Pulse integration tests (22 tests)
    └── shared/
        └── observability/          # Cross-component integration tests
```

**Total**: 120 tests (116 passing, 4 pre-existing failures in timeout_monitor)

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

- [Testing Standard](doc/guides/testing.md)
- [Context Standard](doc/guides/context.md)

