# [CARD-379] Bump LLM Gateway Adapter Read Timeout to 200s for Cold Starts

> **Status**: Done
> **Created**: 2026-09-19
> **Spec Reference**: REQ-GW-004, REQ-RESIL-001
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Provide 200.0s read timeout runway for dynamic model swapping and cold-start weights loading on local GPU nodes like Spark

---

## 2. What to Build
Update OpenAIProviderAdapter default timeout to 200.0s, update gateway factory and settings registration, add unit tests

---

## 3. Acceptance Criteria (Definition of Done)
- [x] **[REQ-GW-004-TIMEOUT]**: `OpenAIProviderAdapter` default `timeout` parameter is updated to `200.0` seconds (replacing `60.0`), and underlying `httpx.Timeout` uses `read=200.0` and `connect=15.0`.
- [x] **[REQ-GW-FACTORY-TIMEOUT]**: `src/infrastructure/gateway/factory.py` defaults `GATEWAY_DEFAULT_TIMEOUT_SECONDS` to `200.0` seconds.
- [x] **[REQ-GW-SETTINGS-TIMEOUT]**: Dynamic adapter registration in `src/web/routers/settings.py` and `src/application/kernel/agent_kernel.py` uses the 200.0s timeout.
- [x] **[REQ-GW-TEST-001]**: Unit tests in `tests/unit/gateway/` assert `OpenAIProviderAdapter` default `timeout == 200.0` and `_get_client().timeout.read == 200.0`.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
