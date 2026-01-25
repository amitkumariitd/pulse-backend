# Testing Guide

> **Mandatory Rule**: Every code change MUST have tests. See `.augment/rules/rules.md` for enforcement policy.

## Quick Start

```bash
# Run all tests (loads .env.local explicitly)
./scripts/run_tests_local.sh -v

# With coverage
./scripts/run_tests_local.sh --cov=gapi --cov=pulse --cov=shared --cov-report=html
open htmlcov/index.html
```

**Status**: 111/111 tests passing ✅

---

## Run Specific Tests

```bash
# By test type
./scripts/run_tests_local.sh tests/unit/ -v          # All unit tests
./scripts/run_tests_local.sh tests/integration/ -v   # All integration tests

# By component
./scripts/run_tests_local.sh tests/unit/pulse-backend/gapi/ -v
./scripts/run_tests_local.sh tests/unit/pulse-backend/pulse/ -v
./scripts/run_tests_local.sh tests/integration/pulse-backend/gapi/ -v
./scripts/run_tests_local.sh tests/integration/pulse-backend/pulse/ -v

# Shared modules
./scripts/run_tests_local.sh tests/unit/shared/ -v
./scripts/run_tests_local.sh tests/integration/shared/ -v

# Specific file
./scripts/run_tests_local.sh tests/unit/pulse-backend/gapi/test_health.py -v

# Specific function
./scripts/run_tests_local.sh tests/unit/pulse-backend/gapi/test_health.py::test_health_returns_ok -v
```

## Configuration for Tests

Tests require **explicit configuration loading**:

**Local development:**
```bash
# Use the helper script (recommended)
./scripts/run_tests_local.sh [pytest args]

# This script loads .env.local before running pytest
```

**Why explicit loading?**
- Settings class does NOT automatically load `.env` files
- Ensures explicit configuration in all environments
- No accidental fallback to wrong config
- Production-like behavior

**Other environments:**
- **CI/CD**: Environment variables set in `.github/workflows/ci-cd.yml`
- **Docker**: Environment variables set in `docker-compose.test.yml`

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

**Tests failing with "Field required" validation errors?**
```bash
# Make sure you're using the test script
./scripts/run_tests_local.sh -v

# Or ensure .env.local has all required fields
```

**`pytest` command not found?** The script uses `python -m pytest`:
```bash
./scripts/run_tests_local.sh -v
```

**Import errors?** Make sure you're in the repo root:
```bash
cd /Users/amitkumar/learn/pulse-backend
./scripts/run_tests_local.sh -v
```

**Missing dependencies?**
```bash
pip install -r requirements.txt
```

---

## See Also

- [Testing Standard](doc/guides/testing.md)
- [Context Standard](doc/guides/context.md)

