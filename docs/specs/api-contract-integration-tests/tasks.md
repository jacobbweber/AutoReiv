# Task Breakdown: Gateway, Wiki & Settings End-to-End API Contract Integration Tests

> **Spec Status**: Implemented  
> **Target Release**: Milestone 10 (v0.10.0)  
> **Card Reference**: [CARD-036](file:///.github/cards/CARD-036-gateway-wiki-and-settings-end-to-end-api-contract-integration-tests.md)  
> **Design Reference**: [design.md](file:///d:/Projects/Active/AutoReiv/docs/specs/api-contract-integration-tests/design.md)  
> **Requirements Reference**: [requirements.md](file:///d:/Projects/Active/AutoReiv/docs/specs/api-contract-integration-tests/requirements.md)

---

## Vertical Slices & Implementation Tasks

### Slice 1: Multi-Provider Gateway API Integration Suite
- [x] **Task 1.1**: Author `tests/integration/test_gateway_contract_api.py` validating `/api/models/discover` and `/api/settings/presets` (`[REQ-API-001]`).

### Slice 2: Wiki Studio & Graph API Integration Suite
- [x] **Task 2.1**: Author `tests/integration/test_wiki_contract_api.py` validating full note CRUD, tree traversal, graph extraction, and chat export (`[REQ-API-002]`).

### Slice 3: Settings Studio & Secret Masking API Integration Suite
- [x] **Task 3.1**: Author `tests/integration/test_settings_contract_api.py` validating provider persistence, matrix updates, system info topics, and secret masking (`[REQ-API-003]`).


### Slice 4: Full Suite Pre-Flight & Gate Closure
- [x] **Task 4.1**: Execute `pytest` across unit and integration suites (`[REQ-API-004]`).
- [x] **Task 4.2**: Execute `npm run preflight` to confirm 100% pass rate across all 6 gates.
- [x] **Task 4.3**: Author ADR-0036 and sync `docs/rtm.json` with `[REQ-API-001]` through `[REQ-API-004]`.
- [x] **Task 4.4**: Update `CHANGELOG.md` under `[Unreleased]` and conclude session.

