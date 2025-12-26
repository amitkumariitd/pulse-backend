# Repo Context – Pulse Backend

## What this repo is
This is the `pulse-backend` monorepo containing multiple components that will evolve into separate deployables.

**Today (Single Deployable):**
- One deployable containing all components: `gapi` + `pulse`

**Future (3 Deployables, 2 Repos):**

**Repo 1: `pulse-backend` (this repo)**
- Deployable 1: `pulse_api` - HTTP API for orders
- Deployable 2: `pulse_background` - SQS consumer / background worker
- Both share the same `pulse` service code (different entry points)

**Repo 2: `gapi` (future separate repo)**
- Deployable 3: `gapi` - HTTP gateway

---

## Components

1) **GAPI**
   - External-facing gateway API
   - Accepts trading requests from external systems (e.g. TradingView)
   - Authenticates, validates, and acknowledges requests
   - Forwards valid requests to Pulse service
   - Future: Will be extracted to separate repo

2) **Pulse**
   - Internal service that owns the trading order domain
   - Persists orders
   - Manages order state transitions
   - Processes orders and performs execution workflows
   - Will have two entry points: HTTP API (`pulse_api`) and background worker (`pulse_background`)

---

## Service boundaries (non-negotiable)

**GAPI ↔ Pulse: Strict HTTP-only boundary**
- GAPI and Pulse are **separate services** (different repos in future)
- GAPI must NEVER import code from Pulse
- Pulse must NEVER import code from GAPI
- Communication between GAPI and Pulse MUST happen via **HTTP APIs only**

**Pulse API ↔ Pulse Background: Shared codebase**
- `pulse_api` and `pulse_background` are different deployables of the same service
- They share all domain logic, repositories, and utilities
- Only entry points differ (HTTP vs background worker)

---

## Technology choices
- Language: Python
- Framework: FastAPI
- API style: REST
- Services are mounted under distinct base paths
- Clear separation of API layer and domain logic

---

## API routing model
- **GAPI (public)**
  - Base path: `/api`
  - Example: `POST /api/orders`
- **Pulse (internal)**
  - Base path: `/internal`
  - Example: `POST /internal/orders`

Public clients must never call internal endpoints.

---

## API contracts (source of truth)
All API contracts live under:
doc/contract/


They are split as follows:
- `common.md`
  Shared schemas, headers, enums, and error formats
- `gapi.md`
  Public-facing GAPI endpoints
- `pulse.md`
  Internal Pulse service endpoints

No endpoint, request, or response shape may be implemented
unless it is defined in these contract files.

---

## Core domain language
- **Order**: A request to buy or sell an instrument
- **Instrument**: Tradable symbol (e.g. NSE:RELIANCE)
- **Order State**: Explicit lifecycle managed by Order Service
- **Source**: Origin of the order (TradingView, API client, etc.)

Domain language inside code uses **business terms only**
(e.g. `Order`, `process_order`, `OrderState`).

Service terms (`pulse`, `gapi`) are used **only for service boundaries**.

---

## Order processing model (v1)
- Order submission is idempotent
- Acceptance does not guarantee execution
- Pulse service owns all state transitions
- Processing may be synchronous initially, but must allow async later
- Failures are explicit and observable

---

## Security & safety
- GAPI is authenticated
- All order inputs are strictly validated
- Idempotency is mandatory for order creation
- Secrets, tokens, and credentials must never be logged
- All processing must be traceable via request_id and order_id

---

## Non-goals (v1)
- Portfolio or PnL calculation
- Risk or margin checks
- Multi-account trading
- Payments, settlement, or reconciliation
- UI or frontend-specific logic

---

## Quality bar
- Clear separation between GAPI and Pulse
- Explicit and tested order state transitions
- Deterministic behavior
- Small, reviewable changes

