# [CARD-018] Skill Pack Hierarchy, Deterministic Guardrails, and System Documentation Browser

> **Status**: Done  
> **Created**: 2026-08-23  
> **Spec Reference**: `docs/specs/skill-pack-guardrails-and-system-docs/`  
> **Labels**: `type:feature`, `milestone:18`, `skills`, `agents`, `docs`

---

## 1. Why / Intent
Provide operators with:
1. Low-friction hierarchical Skill Pack grouping with master bundle toggles and granular tool access control.
2. Deterministic, unyielding guardrails that reject hallucinated tools, malformed slugs, invalid enums, and out-of-bound turn limits before saving to SQLite.
3. An in-app System Documentation & Specs Browser in the Control Plane SPA allowing operators to search and read platform specifications, ADRs, SDLC invariants, and RTM traceability.

---

## 2. What to Build
- `src/application/skills/manifest.py`: Skill Pack clustering manifests (`[REQ-SKIL-001]`).
- `src/domain/agents/guardrails.py`: `AgentProfileGuardrail` invariant validator (`[REQ-SKIL-003]`).
- `src/application/web/system_docs_service.py`: Safe documentation tree indexing and content retrieval (`[REQ-SKIL-004]`).
- `src/web/templates/index.html` & `src/web/static/app.js`: Hierarchical Skill Pack UI in Agent Forge and `#view-docs` reader tab (`[REQ-SKIL-002]`, `[REQ-SKIL-005]`).

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SKIL-001]`: `GET /api/skills/catalog` returns grouped `skill_packs` alongside atomic `tools`.
- [x] `[REQ-SKIL-002]`: Agent Forge Character Sheet renders hierarchical collapsible Skill Packs with master checkbox toggles.
- [x] `[REQ-SKIL-003]`: Deterministic guardrail engine rejects invalid slugs, hallucinated tools, malformed purposes/tones, and out-of-bound turn limits.
- [x] `[REQ-SKIL-004]`: `GET /api/docs/nav` and `GET /api/docs/content` securely serve repository docs with path traversal protection.
- [x] `[REQ-SKIL-005]`: Control Plane `[📖 System & Specs]` tab renders searchable document tree and formatted markdown reader.
- [x] 210/210 unit and integration tests passing cleanly via `pytest`.
- [x] Zero lint errors via `ruff check .`.
- [x] `verify_rtm.py --pre-flight` validates all 106 requirements.

---

## 4. Constraints & Honor Flags
- Zero breaking changes to existing agent profiles or API clients.
- Single isolated `feat/skill-pack-guardrails-and-system-docs` branch.
