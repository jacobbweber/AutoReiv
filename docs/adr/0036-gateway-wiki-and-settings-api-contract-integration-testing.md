# ADR-0036: Gateway Wiki and Settings API Contract Integration Testing

## Context and Problem Statement
Prior to this work, frontend and backend testing was split between low-level unit tests and Playwright browser smoke tests. End-to-end HTTP API contracts connecting JSON request bodies to FastAPI endpoint handlers (model discovery normalization, wiki vault CRUD lifecycles, and settings persistence) were not exercised comprehensively in isolated integration test suites.

## Decision Drivers
- **API Contract Verification**: Ensure FastAPI request/response models match expected frontend schemas and handle error codes (400, 404, 502) gracefully.
- **Isolated Hermetic Test Fixtures**: Use temporary test SQLite databases and scratch directories (`tmp_path`) to ensure tests never write to user production vaults or databases.
- **Continuous Integration Speed**: Execute full integration test suites in < 5 seconds.

## Considered Options
1. **Option 1**: Rely only on browser E2E Playwright tests against a live server.
2. **Option 2 (Accepted)**: Implement dedicated FastAPI TestClient integration test suites for each major subsystem (`test_gateway_api.py`, `test_wiki_api.py`, `test_settings_api.py`).

## Decision Outcome
Chosen Option: **Option 2**.

### Positive Consequences
- Full coverage of model discovery fallback routing, full wiki note CRUD and graph serialization, and settings persistence.
- Fast, deterministic execution during Pytest without external network dependencies.
- Enhanced confidence when refactoring backend services and routing layers.

### Negative Consequences / Trade-offs
- Additional maintenance of integration test files as API schemas evolve.
