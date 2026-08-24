# Requirements Specification: Gateway, Wiki & Settings End-to-End API Contract Integration Tests

> **Spec Status**: Approved  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-036](file:///.github/cards/CARD-036-gateway-wiki-and-settings-end-to-end-api-contract-integration-tests.md)  

> **Primary Component**: AutoReiv FastAPI Backend API & TestClient Integration Suites (`src/web/app.py`, `tests/integration/`)

---

## 1. Executive Summary & Intent

As part of Milestone 10 (P1 Quality & Testability), **CARD-036** establishes end-to-end FastAPI TestClient integration test suites for the primary backend sub-services: Multi-Provider Gateway & Discovery, Wiki Vault & Knowledge Graph, and Settings Configuration & Secret Masking. These tests verify JSON schema integrity, error status codes (400, 404, 422, 502), path sanitization, and security invariants across HTTP lifecycles.

---

## 2. EARS User Stories & Functional Requirements

### [REQ-API-001] Multi-Provider Gateway & Model Discovery API Contract
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide end-to-end integration tests in `tests/integration/test_gateway_contract_api.py` validating `/api/models/discover` across mock providers (Ollama, OpenAI, OpenRouter, Groq, DeepSeek), verifying fallback mechanisms, timeout handling, and model list normalization.

### [REQ-API-002] Wiki Studio Vault & Knowledge Graph API Contract
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide end-to-end integration tests in `tests/integration/test_wiki_contract_api.py` validating note creation (`POST /api/wiki/note`), reading (`GET /api/wiki/note`), updating (`PUT /api/wiki/note`), deletion (`DELETE /api/wiki/note`), search (`GET /api/wiki/search`), tree traversal (`GET /api/wiki/tree`), direct chat export (`POST /api/export/wiki`), and graph relationship parsing (`GET /api/wiki/graph`).

### [REQ-API-003] Settings Configuration & Secret Masking API Contract
- **EARS Pattern**: Ubiquitous
- **Requirement**: The system **shall** provide end-to-end integration tests in `tests/integration/test_settings_contract_api.py` validating provider persistence (`POST /api/settings/providers`), purpose matrix binding (`POST /api/settings/matrix`), preset retrieval (`GET /api/settings/presets`), system info topics (`GET /api/system-info/topics`), and asserting zero leakage of unmasked API keys in JSON responses.

### [REQ-API-004] Pre-Flight Gate & Pytest Integration
- **EARS Pattern**: State-Driven
- **Requirement**: When executing `pytest` or `npm run preflight`, the system **shall** execute all integration suites (`test_gateway_contract_api.py`, `test_wiki_contract_api.py`, `test_settings_contract_api.py`) with 100% green status.


---

## 3. Acceptance Criteria

- [ ] `AC-1`: `tests/integration/test_gateway_api.py` passes covering `/api/models/discover` and error handling.
- [ ] `AC-2`: `tests/integration/test_wiki_api.py` passes covering full CRUD, tree, search, graph, and export.
- [ ] `AC-3`: `tests/integration/test_settings_api.py` passes covering provider updates, matrix, system info, and secret masking.
- [ ] `AC-4`: `npm run preflight` executes all 6 pre-flight gates cleanly with 0 failures.
