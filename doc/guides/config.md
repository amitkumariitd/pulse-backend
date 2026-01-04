# Configuration Standard

## Goals

- Same code, different configuration across **local / dev / stage / prod**.
- No environment-specific values hardcoded in code.
- All configuration discoverable, validated, and documented.

## Single Configuration Layer

- Each service MUST have a single configuration layer (e.g. `config` module).
- All other code MUST read configuration only through this layer, **never directly from `os.environ`**.
- The configuration layer is responsible for:
  - Reading environment variables / secret stores / files.
  - Applying defaults.
  - Type conversion.
  - Validation and fail-fast behavior.

## What Belongs in Configuration

Configuration values (vary by environment):

- Database URLs / hosts / ports / names.
- Cache / queue / message-broker endpoints.
- URLs of other services (e.g. Pulse, GAPI, external APIs).
- Log level, debug flag, and tracing settings.
- Timeouts, retry counts, and rate limits.
- Feature flags.
- External resource identifiers (buckets, topics, queues, etc.).

Code values (same across environments):

- Business rules and domain logic.
- Data model and API contracts.
- Internal constants that are not environment-specific.

## Environment Variables as Primary Interface

- Every configuration item MUST be exposed via a clearly named environment variable.
- The **same variable names MUST be used in all environments**; only values change.
- Do NOT encode the environment in the variable name (e.g. avoid `DB_URL_DEV`, `DB_URL_PROD` in code).
- Local, dev, stage, and prod MUST all rely on environment variables as the primary configuration mechanism.

## Environment Profiles

### Local Development (`ENVIRONMENT=local`)

**Configuration sources (in order of precedence):**
1. Real environment variables (highest priority)
2. `.env.local` (gitignored, local secrets and overrides)
3. `.env.common` (committed, shared defaults)

**Setup:**
- Copy `.env.example` to `.env.local`
- Set `ENVIRONMENT=local` in `.env.local`
- Add local secrets (e.g., `PULSE_DB_PASSWORD=changeme`)
- `.env.local` is gitignored and never committed

**Files:**
- `.env.common` - Committed shared defaults (no secrets)
- `.env.local` - Gitignored local overrides (can contain secrets)
- `.env.example` - Committed template showing all required fields

### india-stage1 / india-prod1 / india-prod2

**Configuration sources:**
- Real environment variables ONLY (no `.env` files in deployed containers)
- ECS task definitions / container environment variables
- AWS SSM Parameter Store / Secrets Manager (injected as env vars)

**Setup:**
- Set `ENVIRONMENT=india-stage1` (or `india-prod1`, `india-prod2`) via ECS
- All other config via ECS env vars or SSM/Secrets Manager
- No `.env` files exist in deployed containers

**Security:**
- No real environment-specific values (URLs, credentials, secrets) may be committed to the repo
- All secrets MUST come from AWS Secrets Manager or SSM Parameter Store

## Secrets Handling

- Secrets (passwords, tokens, keys, certificates) MUST NOT be committed to Git.
- Secrets SHOULD be stored in AWS Secrets Manager or AWS SSM Parameter Store and injected via environment variables.
- The configuration layer MUST NOT log secret values; at most, log which keys are loaded or use masked values.

## Validation and Fail-Fast Behavior

On startup, the configuration layer MUST:

- Validate that all required configuration keys are present.
- Validate types and basic constraints (e.g. ports are integers, timeouts are positive).
- Fail fast with a clear error message if any required value is missing or invalid.

**Implementation:**
- Almost all fields are **required** (no defaults in code)
- Only `service_name` has a default (`"pulse-backend"`)
- Shared defaults live in `.env.common` (committed)
- Missing required fields cause immediate validation error on startup

**Example:**
```python
from config.settings import get_settings

settings = get_settings()  # Fails fast if ENVIRONMENT or other required fields missing
```

## Testing and Configuration

### Unit Tests

- May override configuration via in-memory objects or test-specific environment variables.
- MUST test behavior for:
  - Missing required values.
  - Defaults being applied.
  - Overrides via environment variables.

### Integration Tests

- MUST use the same configuration mechanism as production (the central configuration layer).
- MUST use separate test resources (e.g. test database, test queues) with the **same variable names** but different values.

## Configuration Reference

All configuration keys are defined in `config/settings.py`. See `.env.example` for a complete template.

### Core

| Key | Type | Required | Default | Example |
|-----|------|----------|---------|---------|
| `ENVIRONMENT` | string | **Yes** | - | `local`, `india-stage1`, `india-prod1` |
| `SERVICE_NAME` | string | No | `pulse-backend` | `pulse-backend` |

### HTTP Server

| Key | Type | Required | Default (in .env.common) | Example |
|-----|------|----------|--------------------------|---------|
| `APP_HOST` | string | **Yes** | `0.0.0.0` | `0.0.0.0` |
| `APP_PORT` | int | **Yes** | `8000` | `8000` |

### Logging / Tracing

| Key | Type | Required | Default (in .env.common) | Example |
|-----|------|----------|--------------------------|---------|
| `LOG_LEVEL` | string | **Yes** | `INFO` | `DEBUG`, `INFO`, `WARNING` |
| `TRACING_ENABLED` | bool | **Yes** | `false` | `true`, `false` |

### Database (PostgreSQL)

| Key | Type | Required | Default (in .env.common) | Example |
|-----|------|----------|--------------------------|---------|
| `PULSE_DB_HOST` | string | **Yes** | - | `localhost`, `db.example.com` |
| `PULSE_DB_PORT` | int | **Yes** | `5432` | `5432` |
| `PULSE_DB_USER` | string | **Yes** | `pulse` | `pulse` |
| `PULSE_DB_PASSWORD` | string | **Yes** | - | `changeme` (never commit!) |
| `PULSE_DB_NAME` | string | **Yes** | `pulse` | `pulse` |

### Internal Service URLs (Optional)

| Key | Type | Required | Default | Example |
|-----|------|----------|---------|---------|
| `GAPI_BASE_URL` | string | No | `None` | `http://localhost:8000/gapi` |
| `PULSE_API_BASE_URL` | string | No | `None` | `http://localhost:8001` |

## Change Management

- Any change to configuration shape (adding/removing/renaming keys) MUST go through PR review.
- Risky configuration changes SHOULD roll out in order: **dev → stage → prod**, with validation at each step.
- Ad-hoc manual edits in the cloud console SHOULD be avoided in favour of CI/CD or infrastructure-as-code.

