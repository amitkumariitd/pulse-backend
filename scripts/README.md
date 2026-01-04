# Scripts

Helper scripts for development and testing.

## run_local.sh

Runs the application locally with `.env.local` explicitly loaded.

**Usage:**
```bash
# Start the application
./scripts/run_local.sh

# With custom uvicorn args
./scripts/run_local.sh --host 0.0.0.0 --port 8080
```

**Why this script?**

The Settings class does NOT automatically load `.env` files. This ensures:
- Explicit configuration in all environments
- No accidental fallback to wrong config
- Production-like behavior

This script loads `.env.local` into the environment before starting uvicorn.

**Requirements:**
- `.env.local` must exist in the repository root
- `.env.local` must contain all required configuration fields

---

## run_tests_local.sh

Runs pytest with `.env.local` explicitly loaded.

**Usage:**
```bash
# Run all tests
./scripts/run_tests_local.sh -v

# Run specific tests
./scripts/run_tests_local.sh tests/unit/services/gapi/ -v

# With coverage
./scripts/run_tests_local.sh --cov=gapi --cov=pulse --cov=shared --cov-report=html
```

**Why this script?**

The Settings class does NOT automatically load `.env` files. This ensures:
- Explicit configuration in all environments
- No accidental fallback to wrong config  
- Production-like behavior in tests

This script loads `.env.local` into the environment before running pytest.

**Requirements:**
- `.env.local` must exist in the repository root
- `.env.local` must contain all required configuration fields

See `TESTING.md` for more details.

