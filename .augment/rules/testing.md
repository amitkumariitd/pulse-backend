# Testing Rules (MANDATORY)

**Every code change MUST have corresponding tests. No exceptions.**

See `TESTING.md` for detailed guide, commands, and examples.

---

## What requires tests

- **New endpoints** → integration tests (success, validation, auth)
- **New functions/methods** → unit tests (behavior, edge cases, errors)
- **Modified behavior** → regression tests (new + existing behavior)
- **Middleware changes** → request/response/context tests
- **Shared utilities** → comprehensive unit tests

---

## Requirements

- Tests MUST be written BEFORE marking work as complete
- Tests MUST pass before considering the change done
- Tests MUST verify actual behavior, not just call the code
- Do NOT disable tests to make builds pass
- Do NOT skip tests because "it's simple" or "obvious"

---

## Location

- Unit tests: `tests/unit/`
- Integration tests: `tests/integration/`
- Follow existing directory structure

---

## Enforcement

If you make a code change without adding tests:
1. You MUST add tests before proceeding
2. You MUST run tests and verify they pass
3. You MUST update test count in TESTING.md if applicable

---

## When in doubt

- Re-read `TESTING.md` for commands and examples
- Follow the AAA pattern (Arrange, Act, Assert)
- Ask for clarification instead of skipping tests

