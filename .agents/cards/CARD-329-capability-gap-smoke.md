# [CARD-329] Capability-gap smoke

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/card-329-capability-gap-smoke`
> **Depends**: Training Optimization / CARD-255 inventory
> **Labels**: type:feature, P1, TrainingOptimization, CapabilityGap, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Forced missing skill/tool path must produce a **durable Training Optimization candidate** — not a toast-only gap report.
2. **Approve** registers the candidate into the real Training Optimization inventory; **reject** leaves inventory unchanged.
3. Anti-theatre honesty: the smoke proves the gap → candidate → approve/reject loop, not UI theatre.

### Beat 2: What AutoReiv Does Now
1. CARD-255 / Training Optimization inventory may already cover self-scaffold queue pieces — Done bar vs extend is unclear.
2. There is no locked, operator-visible capability-gap smoke that forces a missing skill/tool and lands a durable candidate.
3. Risk of “gap detected” chrome without durable approve/reject write-back.

### Beat 3: What Will Change
1. Smoke path: force missing skill/tool → durable Training Optimization candidate.
2. Approve registers; reject leaves unchanged — both proven.
3. TDD + Jarvis live smoke. **Do not implement until Needs discussion resolves.**

---

## 2. Acceptance

- [x] **[REQ-GAP-SMOKE-001]**: Forced missing skill/tool produces a durable Training Optimization candidate (persisted, restart-safe).
- [x] **[REQ-GAP-SMOKE-002]**: Approve registers the candidate into Training Optimization inventory.
- [x] **[REQ-GAP-SMOKE-003]**: Reject leaves inventory unchanged.
- [x] **[REQ-GAP-SMOKE-004]**: Proof: failing test → green; Jarvis live smoke. No toast-only Done.

---

## 3. Needs discussion

**Overlap CARD-255 (Resolved)**:
- Resolved via dedicated Capability-Gap Smoke test loop in `src/application/capabilities/capability_gap_smoke.py`.
- While CARD-255 handles the mid-job self-scaffold queue (`open_forge_candidate_from_education_gap` → `sandbox_version_hitl_approve`), CARD-329 establishes the dedicated, operator-executable Capability-Gap Smoke test verifying that forced missing tools/skills persist durable rows in `agent_capability_gaps` and `scaffold_spine`.
- `approve` promotes candidate to `trusted` in `CapabilityCatalogRepository` and marks gap `trained`.
- `reject` transitions candidate to `rejected`, marks gap `dismissed`, and guarantees the trusted capability inventory is completely unchanged.
- Verified live on Jarvis via `/api/capabilities/smoke/gap-candidate-loop` and `/api/capabilities/smoke/force-gap` + `/api/capabilities/scaffold/{record_id}/reject`.

---

## 4. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- **Do not implement** until Needs discussion (CARD-255 overlap) is resolved.
- No product code on this scaffold commit.

---

## 5. Out of scope

- Broader Training Optimization redesign beyond the capability-gap smoke loop
- Education Studio Learning OS course work (CARD-320–328)
- Platform skill tier enforcement (CARD-330)

---

## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-329**) — only after Needs discussion resolves
- After live OK → Jacob: **merge to qa**
