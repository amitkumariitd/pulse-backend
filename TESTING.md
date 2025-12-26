# Testing Guide

## Quick Start

```bash
# Run all tests
python -m pytest

# Verbose output
python -m pytest -v

# With coverage
python -m pytest --cov=services --cov-report=html
open htmlcov/index.html
```

**Status**: 20/20 tests passing ✅

---

## Run Specific Tests

```bash
# By service
python -m pytest services/gapi/tests/
python -m pytest services/order_service/tests/

# By type
python -m pytest services/gapi/tests/unit/          # Unit tests only
python -m pytest services/gapi/tests/integration/   # Integration tests only

# Specific file
python -m pytest services/gapi/tests/unit/test_health.py

# Specific function
python -m pytest services/gapi/tests/unit/test_health.py::test_health_returns_ok
```

---

## Test Structure

```
services/
├── gapi/tests/
│   ├── unit/              # Fast, isolated (4 tests)
│   └── integration/       # End-to-end (6 tests)
└── order_service/tests/
    ├── unit/              # Fast, isolated (4 tests)
    └── integration/       # End-to-end (6 tests)
```

**Total**: 20 tests, 100% coverage

---

## Writing New Tests

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

### Requirements
Every new endpoint MUST have:
- ✅ Success path test
- ✅ Validation failure test (if applicable)
- ✅ Tracing headers test

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

