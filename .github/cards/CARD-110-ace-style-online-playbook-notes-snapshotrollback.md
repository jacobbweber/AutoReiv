# [CARD-110] ACE-style online playbook notes + snapshot/rollback

> **Status**: Ready
> **Created**: 2026-08-30
> **Spec Reference**: `docs/specs/skill-self-improve/`
> **Labels**: `type:feature`, `area:skills`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Tiny ACE-style playbook deltas from execution feedback. Generator / Reflector / Curator are in-process roles on the existing kernel â€” not a second ReAct loop. Snapshot before apply; rollback restores. Never rewrite tool Python mid-turn. If the delta would change `SKILL.md`, park it with CARD-106 `propose_skill` so that HITL gate holds.

## 2. What to Build
- Post-turn Reflector on existing `AgentKernel` (Generator). One small insight per failed turn / checker miss, not a full playbook rewrite.
- Curator: append-only sidecar notes (`PLAYBOOK_NOTES.md` / `notes.jsonl`) and/or `propose_skill` for `SKILL.md` patches. Prefer `propose_skill`.
- Snapshot `$DATA_DIR/skills/<id>/SKILL.md` (+ sidecar) to `snapshots/<utc-iso>/` before apply. Rollback restores. Fail closed if snapshot I/O fails.
- No `src/` Python writes. No second builder class. No LangGraph. Nightly eval is CARD-111, not this card.

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-IMPROVE-001]`: Failed turn / checker miss produces at most one tiny delta. Live `SKILL.md` is not fully rewritten in the same turn.
- [ ] `[REQ-IMPROVE-002]`: Generator is existing `AgentKernel`. Reflector + Curator in-process. No second kernel, no ACE GitHub vendor.
- [ ] `[REQ-IMPROVE-003]`: No Python tool / `BuiltinSkill` writes under `src/` mid-turn. Python-shaped deltas stay `propose_tool` drafts.
- [ ] `[REQ-IMPROVE-004]`: Snapshot before apply. Rollback restores. Snapshot failure skips apply.
- [ ] `[REQ-IMPROVE-005]`: `SKILL.md` patches go through `propose_skill` draft + HITL. Approve does not write disk. Commit is CARD-107.
- [ ] `[REQ-IMPROVE-006]`: Optional sidecar is append-only and does not modify `SKILL.md`. Promotion still uses `propose_skill`.
- [ ] `[REQ-IMPROVE-016]`: Online path does not enqueue or block on the nightly routine.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- CARD-106 gate holds. No live tool codegen. No SkillOpt pip. No LangGraph. No weight training.
- Spec: `docs/specs/skill-self-improve/`.
