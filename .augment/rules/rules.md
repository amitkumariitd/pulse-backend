# Augment Rules – Pulse Backend

These rules define how code must be written and changed in this repo.
They are mandatory and must be followed for every task.

---

## Git and version control rules (mandatory)

- **ALWAYS ask for confirmation before committing code. Explicit approval required. do not assume implementation is correct**
- Do NOT commit without explicit user approval.
- Show what will be committed and wait for user confirmation.
- Do NOT push to remote without explicit permission.
- Do NOT perform rebase without explicit permission.
- Always run test before commit

---

## Service boundary rules (critical)

**GAPI ↔ Pulse: Strict HTTP-only boundary**
- GAPI and Pulse are separate services (different repos in future)
- GAPI must NEVER import code from Pulse
- Pulse must NEVER import code from GAPI
- Communication between GAPI and Pulse MUST happen via HTTP APIs only
- Do NOT bypass service boundaries by calling Python functions across services

**Pulse API ↔ Pulse Background: Shared codebase**
- `pulse_api` and `pulse_background` are different deployables of the same `pulse` service
- They CAN share all domain logic, repositories, and utilities
- Only entry points differ (HTTP vs background worker)

---

## API contract rules (non-negotiable)

- All APIs MUST be defined in `contracts/` before implementation.
- Do NOT invent endpoints, request fields, response fields, or error formats.
- GAPI endpoints must exist only in `contracts/service-groups/pulse-backend/services/gapi-api/api.md`.
- Pulse endpoints must exist only in `contracts/service-groups/pulse-backend/services/pulse-api/api.md`.
- Shared schemas must come only from `contracts/schemas/common.md` and `contracts/schemas/common.yaml`.

If a change requires modifying a contract:
1) Update the contract document first
2) Then implement the code

---

## Naming rules

- Use **domain language** inside code:
  - `Order`, `OrderState`, `process_order`
- Use **service language** only at service boundaries:
  - `pulse`, `gapi`
- Do NOT create names like:
  - `PulseOrder`
  - `process_pulse_service`
  - `gateway_service`

Folders represent services. Code represents domain concepts.

---

## Code structure rules

- API route handlers must be thin:
  - authentication
  - input validation
  - delegation only
- Domain logic must live in service/domain layers, not in API routes.
- Order state transitions must happen only inside Pulse service.
- No business logic in GAPI.

---

## Persistence rules

**Repository Pattern (mandatory):**
- Use repository interfaces for ALL persistence.
- Do NOT access storage directly from API routes.
- No shared database assumptions across services.
- In-memory storage is acceptable in v1, but must be swappable.

**PostgreSQL Standards (mandatory):**

All database code MUST follow `contracts/standards/database/README.md`.

Key requirements:
- Use repository pattern for all database access (inherit from BaseRepository)
- Include `request_id` in ALL tables, `origin_*` columns in async-initiating tables
- Use parameterized queries (never string interpolation)
- Use connection pooling with asyncpg
- Use Alembic for schema migrations
- Create history tables with triggers for all tables
- Never store derived/aggregated data (counts, sums)

See `contracts/standards/database/README.md` for principles and `doc/guides/postgres-implementation.md` for Python/asyncpg implementation.

---

## Configuration rules (mandatory)

- **Never use default fallback values for configuration.**
- If a config value is not set, raise an error with a clear message.
- Do NOT use patterns like `config.value or "default"`.
- Always require explicit configuration via environment variables.
- Fail fast at startup if required config is missing.

Example (correct):
```python
base_url = settings.pulse_api_base_url
if not base_url:
    raise ValueError("PULSE_API_BASE_URL must be set")
```

Example (incorrect):
```python
base_url = settings.pulse_api_base_url or "http://localhost:8001"  # ❌ NO!
```

---

## Security rules

- Never log secrets, tokens, credentials, or auth headers.
- Always validate external inputs strictly.
- Idempotency-Key is mandatory for order creation.
- Authentication must be enforced at GAPI boundaries.

---

## Observability rules

- Every request must have a request_id (generate if missing).
- Every order must have a stable order_id.
- Logs must include request_id and order_id where applicable.
- Errors must follow the common error format.

---

## Concurrency rules

**All concurrent code MUST follow `contracts/standards/concurrency/README.md`.**

Key requirements:
- API operations must be idempotent (unique idempotency_key)
- Background workers must use proper locking (pessimistic or optimistic)
- Never use incremental updates (e.g., `count = count + 1`)
- Always recalculate aggregates from source of truth
- Implement timeout monitors for crash recovery

---

## Dependency rules

- Do NOT add new third-party libraries without explicit instruction.
- Prefer standard library where reasonable.
- Avoid premature abstractions and frameworks.

---

## Testing rules

**All testing requirements are defined in `contracts/standards/testing/README.md`.**

Testing is mandatory for all code changes. No exceptions.

Key requirements:
- New endpoints → integration tests (success, validation, auth)
- New functions/methods → unit tests (behavior, edge cases, errors)
- Modified behavior → regression tests (new + existing behavior)
- Tests MUST pass before considering the change done
- Do NOT disable tests to make builds pass

See `TESTING.md` for detailed guide, commands, and examples.

---

## Change discipline

- Prefer small, reviewable changes.
- For non-trivial work:
  - propose a short plan before implementing
- Do NOT refactor unrelated code unless explicitly requested.

---

## When in doubt

- Re-read `.augment/context.md`
- Re-read `contracts/*`
- Ask for clarification instead of guessing
