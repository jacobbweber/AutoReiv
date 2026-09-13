# [CARD-155] Repository Constitution and Agentic Rules Ingestion for Local LLMs

> **Status**: Done
> **Created**: 2026-09-03
> **Closed**: 2026-09-08
> **Spec Reference**: `docs/specs/project-agents-standardization/` (CARD-190)
> **Labels**: `type:feature`, `AutoReiv.SDLC`, `AutoReiv.Developer`

---

## 1. Why / Intent

When operating on a codebase, an agent needs to automatically discover and respect the project's specific working agreements and rules.

*Architectural Resolution*: Instead of ingesting fragmented, vendor-specific instruction files (`CLAUDE.md`, `.cursorrules`), AutoReiv adopted the official **DotAgents Protocol (`.agents/`)** and canonical **`AGENTS.md`** open standard across all projects in **CARD-190** (`[REQ-SDLC-060]` - `[REQ-SDLC-063]`). The Platform **Developer Agent** (CARD-181) operates natively within this canonical directory structure (`.agents/cards/`, `.agents/specs/`, `.agents/steering/`, `.agents/skills/`), with strict rules of engagement grounded without vendor lock-in.

---

## 2. What Was Built

1. **Official Open Standards Adoption (`.agents/` & `AGENTS.md`)**:
   - Standardized project-level governance strictly on open standards (`.agents/` directory tree and `AGENTS.md` master constitution). Vendor-specific instruction files are intentionally excluded.
2. **Platform Developer Agent Ingestion (CARD-181 & CARD-190)**:
   - Developer agent automatically grounds to the selected project root, navigates `.agents/` steering documents (`product.md`, `tech.md`, `structure.md`, `roadmap.md`), and discovers project skills under `.agents/skills/`.
3. **Automated Verification**:
   - Verified end-to-end via CARD-190 tests (`tests/unit/sdlc/test_card_190_dotagents_standard.py`) and CARD-192 SentinelPulse project build.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-RULES-001]`: Adopt canonical open standard (`AGENTS.md` and `.agents/` protocol) for project rules and constitutions.
- [x] `[REQ-RULES-002]`: Developer Agent operates against `.agents/` and `AGENTS.md` when planning and building features.
- [x] `[REQ-RULES-003]`: Reject vendor-specific instruction files in favor of unified DotAgents open standard.
- [x] `[REQ-RULES-004]`: Automated unit tests verify discovery and resolution logic (`tests/unit/sdlc/test_card_190_dotagents_standard.py`).
- [x] `[REQ-RULES-005]`: Zero linting errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Zero vendor-specific instruction files or third-party product names in project artifacts.
- Official open standards only (`.agents/` and `AGENTS.md`).
- Local `qa` branch is source of truth.

