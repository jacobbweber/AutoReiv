# [CARD-106] propose_skill / propose_tool / propose_workflow HITL drafts

> **Status**: Ready
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/agent-builder-hitl/`
> **Labels**: `type:feature`, `area:skills`, `area:orchestration`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
HITL drafts for skill, tool, and workflow packs. Reuse the CARD-101 `proposals` table (`kind` already includes `skill|tool|workflow`) and `pending_approvals`. Never auto-write `SKILL.md` or Python tools. Payload is what / why / how / where (`$DATA_DIR` path). CARD-078 sprawl warning at ~12: prefer more tools/skills on an existing specialist vs a new agent.

## 2. What to Build
- `propose_skill`, `propose_tool`, `propose_workflow` on the existing `AgentBuilderSkill` (do not add a second builder class).
- Each call writes a `proposals` row status `draft` plus a `pending_approvals` park. No `SKILL.md` write. No Python module write. No Job auto-run.
- Payload JSON: `what`, `why`, `how`, `where`. Jail `where` under `$DATA_DIR/skills`.
- Approve marks `approved` and does **not** write disk. Reject marks `rejected`. Same Chat HITL path as `propose_followup`.
- Workflow in this card is a playbook SOP, not job-template YAML.
- Soft sprawl warning when allowlist would be >= 12. Does not block the draft.

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-BUILD-001]`: `propose_skill` writes `kind=skill` status `draft` plus HITL park. No `SKILL.md` write.
- [ ] `[REQ-BUILD-002]`: `propose_tool` writes `kind=tool` status `draft` plus HITL park. No Python tool file.
- [ ] `[REQ-BUILD-003]`: `propose_workflow` writes `kind=workflow` status `draft`. No auto-run. Not job-template YAML.
- [ ] `[REQ-BUILD-004]`: Payload is what / why / how / where. `where` jailed under `$DATA_DIR`. Missing field fails closed.
- [ ] `[REQ-BUILD-005]`: Propose / Approve / Reject do not write `SKILL.md` or `src/` Python skills.
- [ ] `[REQ-BUILD-006]`: CARD-078 warning when allowlist would be >= 12 or a new agent is proposed instead of extending a specialist. Soft, not a block.
- [ ] `[REQ-BUILD-007]`: Same `proposals` table and `pending_approvals` as CARD-101. No second store.
- [ ] `[REQ-BUILD-008]`: Approve does not write disk. Reject discards.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Extend `AgentBuilderSkill`. No second builder. No SkillOpt. No ACE. No LangGraph. No live Okta.
- `followup_job` semantics stay. Disk commit is CARD-107.
- Spec: `docs/specs/agent-builder-hitl/`.