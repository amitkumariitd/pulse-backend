# Augment Rules – Pulse Backend

These rules define how code must be written and changed in this repo.
They are mandatory and must be followed for every task.

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

- All APIs MUST be defined in `doc/contract/` before implementation.
- Do NOT invent endpoints, request fields, response fields, or error formats.
- GAPI endpoints must exist only in `doc/contract/gapi.md`.
- Pulse endpoints must exist only in `doc/contract/pulse.md`.
- Shared schemas must come only from `doc/contract/common.md`.

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

- Use repository interfaces for persistence.
- Do NOT access storage directly from API routes.
- No shared database assumptions across services.
- In-memory storage is acceptable in v1, but must be swappable.

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

## Dependency rules

- Do NOT add new third-party libraries without explicit instruction.
- Prefer standard library where reasonable.
- Avoid premature abstractions and frameworks.

---

## Testing rules

**All testing requirements are defined in `.augment/rules/testing.md`.**

Testing is mandatory for all code changes. No exceptions.

---

## Change discipline

- Prefer small, reviewable changes.
- For non-trivial work:
  - propose a short plan before implementing
- Do NOT refactor unrelated code unless explicitly requested.

---

## When in doubt

- Re-read `.augment/context.md`
- Re-read `doc/contract/*`
- Ask for clarification instead of guessing
