# Repo Context – Trading Backend Monorepo

## What this repo is
This repo is a backend monorepo that contains two logically and operationally
separate services:

1) **GAPI**
   - External-facing gateway API
   - Accepts trading requests from external systems (e.g. TradingView)
   - Authenticates, validates, and acknowledges requests
   - Forwards valid requests to Order Service

2) **Order Service**
   - Internal service that owns the trading order domain
   - Persists orders
   - Manages order state transitions
   - Processes orders and performs execution workflows

Both services live in the same repo today, and will deploy together initially
** easily split into separate repos in the future**.

---

## Service boundaries (non-negotiable)
- GAPI and Order Service are **separate services**, even if:
  - they run in the same process
  - they are deployed together initially
- GAPI must not contain order domain logic
- Order Service must not depend on GAPI code
- Communication between services is via **HTTP APIs**, not direct Python imports

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
- **Order Service (internal)**
  - Base path: `/internal/orders`
  - Example: `POST /internal/orders`

Public clients must never call internal endpoints.

---

## API contracts (source of truth)
All API contracts live under:
docs/contracts/


They are split as follows:
- `common.md`  
  Shared schemas, headers, enums, and error formats
- `gapi.md`  
  Public-facing GAPI endpoints
- `order_service.md`  
  Internal Order Service endpoints

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

Service terms (`order_service`, `gapi`) are used **only for service boundaries**.

---

## Order processing model (v1)
- Order submission is idempotent
- Acceptance does not guarantee execution
- Order Service owns all state transitions
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
- Clear separation between GAPI and Order Service
- Explicit and tested order state transitions
- Deterministic behavior
- Small, reviewable changes

