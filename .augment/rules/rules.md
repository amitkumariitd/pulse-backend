# Augment Rules – Backend Monorepo

These rules define how code must be written and changed in this repo.
They are mandatory and must be followed for every task.

---

## Service boundary rules (critical)

- GAPI and Order Service are separate services, even though they live in the same repo.
- GAPI must NEVER import code from Order Service.
- Order Service must NEVER import code from GAPI.
- Communication between GAPI and Order Service MUST happen via HTTP APIs only.
- Do NOT bypass service boundaries by calling Python functions across services.

---

## API contract rules (non-negotiable)

- All APIs MUST be defined in `docs/contracts/` before implementation.
- Do NOT invent endpoints, request fields, response fields, or error formats.
- GAPI endpoints must exist only in `docs/contracts/gapi.md`.
- Order Service endpoints must exist only in `docs/contracts/order_service.md`.
- Shared schemas must come only from `docs/contracts/common.md`.

If a change requires modifying a contract:
1) Update the contract document first
2) Then implement the code

---

## Naming rules

- Use **domain language** inside code:
  - `Order`, `OrderState`, `process_order`
- Use **service language** only at service boundaries:
  - `order_service`, `gapi`
- Do NOT create names like:
  - `OrderServiceOrder`
  - `process_order_service`
  - `gateway_service`

Folders represent services. Code represents domain concepts.

---

## Code structure rules

- API route handlers must be thin:
  - authentication
  - input validation
  - delegation only
- Domain logic must live in service/domain layers, not in API routes.
- Order state transitions must happen only inside Order Service.
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
- Re-read `docs/contracts/*`
- Ask for clarification instead of guessing
