# [CARD-218] Self-Scaffold Spine (Candidate → Sandbox → Version → HITL → Trusted)

> **Status**: Done
> **Marathon self-validate**: promoted 2026-09-11 after live proofs on feat standing path.
> **Created**: 2026-09-10
> **Spec Reference**: Design room after CARD-217; cite SoK Agentic Skills arXiv 2602.20867; extends propose_skill / propose_tool / HITL / UserSkillCatalog / Capability Catalog C
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`, `AgentForge`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Never trusted by default**: A newly self-authored skill/tool always lands as **candidate** — never jumps to trusted.
2. **One honest path**: draft → sandbox exec → version (snapshot) → HITL approve → trusted. No shortcut write into the trusted catalog.
3. **Rollback is real**: Approving a candidate snapshots the prior trusted revision; rollback restores that prior trusted state (via UserSkillCatalog snapshots + durable spine row).
4. **Unscoped trusted write = reject**: Any attempt to write/promote straight to `trusted` without the spine path fails closed.
5. **Operator path**: Agent Forge shows a **candidate queue** (not a second product). Align with existing `propose_skill` / `propose_tool` / HITL / catalog — extend, do not invent parallel stores.
6. **Proof**: red tests for "candidate cannot run unsandboxed" and "rollback restores prior"; then green. Cite SoK Agentic Skills (arXiv 2602.20867) for skill lifecycle hygiene.

### Beat 2: What AutoReiv Does Now
1. CARD-106 `propose_skill` / `propose_tool` create HITL **draft** proposals; approve does not write disk; `commit_skill_pack` writes via `UserSkillCatalog.save_pack` (with pack snapshots).
2. CARD-217 Capability Catalog indexes entries with trust tiers `candidate|reviewed|trusted`, but has **no write spine** enforcing sandbox → version → HITL → trusted.
3. `UserSkillCatalog.snapshot_pack` / `rollback_pack` exist for pack files — not wired as a standing self-scaffold gate.
4. Agent Forge edits agents/packs; there is no candidate queue for scaffold lifecycle.

### Beat 3: What Will Change
1. Durable `scaffold_spine` rows tracking phase + prior trusted snapshot + sandboxed flag + optional `proposal_id` / capability id.
2. Application `SelfScaffoldSpine`: draft (always candidate), sandbox mark, version/snapshot, HITL approve→trusted, rollback→prior trusted; run gate rejects candidate unsandboxed; write gate rejects unscoped trusted writes.
3. Capability index stays aligned: draft upserts/keeps `candidate`; approve promotes `trusted`; rollback restores prior tier/content.
4. API + Agent Forge candidate queue (list / sandbox / approve / rollback actions).
5. Proof: red→green for unsandboxed candidate reject + rollback restores prior. Out of scope: full ATF rewrite, Homelab domain outcomes, CARD-219 crash-resume.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-SCAFFOLD-001]**: New skill/tool scaffold always starts at trust tier / phase **candidate** (never trusted by default).
- [x] **[REQ-SCAFFOLD-002]**: Lifecycle path is draft → sandbox_exec → versioned → hitl_approved → trusted; durable SQLite `scaffold_spine` records phase transitions.
- [x] **[REQ-SCAFFOLD-003]**: Candidate **cannot run unsandboxed** — run gate fails closed until sandbox_exec is recorded.
- [x] **[REQ-SCAFFOLD-004]**: Rollback restores **prior trusted** snapshot (UserSkillCatalog + spine metadata); capability trust restored accordingly.
- [x] **[REQ-SCAFFOLD-005]**: Unscoped write/promote to `trusted` (bypassing spine) is **rejected**.
- [x] **[REQ-SCAFFOLD-006]**: Align with existing propose_skill / propose_tool / HITL / UserSkillCatalog / capability_index — optional `proposal_id` link; no second product store for proposals.
- [x] **[REQ-SCAFFOLD-007]**: Agent Forge candidate queue surfaces pending candidates + sandbox/approve/rollback actions via API.
- [x] **[REQ-SCAFFOLD-008]**: Automated tests: red then green for 003 + 004; ruff clean; CHANGELOG `[Unreleased]`; work on `feat/*` — never merge `qa`/`main`.

---

## 3. Constraints & Honor Flags

- Status: **In Review** (thin spine live on Jarvis).
- Branch: continue `feat/standing-job-graph-runtime`. Never push `qa`/`main`.
- Out of scope: CARD-219 crash-resume (sketch Ready only if 218 solid), ATF/Lab rewrite, Homelab domain outcomes.
- Anti-theatre: durable spine rows + Forge queue + fail-closed gates; cite arXiv 2602.20867.
- Leave CARD-217 In Review unless critical bug.

---

## 4. Modules Likely Touched

- `src/domain/capabilities/` — scaffold models
- `src/application/capabilities/scaffold_spine.py` — spine service + gates
- `src/infrastructure/memory/schema.py` + `repositories/scaffold_spine.py`
- `src/web/routers/capabilities.py` — scaffold API
- `src/web/templates/index.html` + `forge.js` — candidate queue
- `tests/unit/capabilities/test_self_scaffold_spine.py`

---

## 5. Marathon Notes

- Thin slice: spine + gates + Forge queue + catalog alignment. Full sandbox isolation runtime is mark/gate only in this card (honest sandboxed flag), not a new container product.


## 6. Marathon Build Notes (Jarvis 2026-09-10)

- Thin spine on `feat/standing-job-graph-runtime`: domain `ScaffoldRecord`/`ScaffoldPhase`, `SelfScaffoldSpine`, SQLite `scaffold_spine`, Forge candidate queue, `/api/capabilities/scaffold/*`.
- Aligns with capability_index trust tiers + UserSkillCatalog snapshot/rollback; optional `proposal_id` link to HITL drafts.
- Unit: `tests/unit/capabilities/test_self_scaffold_spine.py` — candidate unsandboxed reject (red→green), rollback restores prior trusted, unscoped trusted write reject, Forge queue API.
- CARD-217 left In Review. Never merge/push qa or main.
