# [CARD-107] Agent Builder specialist wired to Job/Phase + data_dir skills (extend AgentBuilderSkill)

> **Status**: In Review
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/agent-builder-hitl/`
> **Labels**: `type:feature`, `area:agents`, `area:skills`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
Agent Builder is a user-facing Chat specialist (not Conductor). It talks to the human, researches, and emits packs into `$DATA_DIR/skills` through the same Skills Studio files. It uses Job/Phase (CARD-096+) and the CARD-099 no-tool planner for research phases. Soft sprawl warnings before commit. User packs are markdown + JSON. Do not write Python `BuiltinSkill` modules under `src/` in this card. Extend the existing `AgentBuilderSkill`; do not invent a second builder.

## 2. What to Build
- Builtin `agent-builder` profile selectable in Chat. Not Conductor: no SDLC card/spec authorship as its job.
- Keep existing tools (`list_available_skills_and_tools`, `propose_agent_specification`, `save_agent_specification`) on `AgentBuilderSkill`. Add `propose_*` (CARD-106) and `commit_skill_pack`.
- Default Chat: one Job + one Phase + `stream_turn`. Goal mode: no-tool linear research phases (survey, draft playbook, declare tools, HITL propose). Research phases do not write `SKILL.md`.
- After HITL Approve, `commit_skill_pack` writes via `UserSkillCatalog.save_pack` jailed to `$DATA_DIR/skills`. Skills Studio can open the same file.
- Soft CARD-078 warning before commit when allowlist would be >= 12 or a new agent is proposed instead of extending a specialist. Not a hard gate.
- Allowlist stays under ~12. Do not mount Coding/SDLC/`cli_exec` tools. Coding, Review, Conductor do not get `propose_skill`.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-BUILD-009]`: `agent-builder` builtin is selectable in Chat. It is not a second Conductor.
- [x] `[REQ-BUILD-010]`: New tools register on existing `AgentBuilderSkill`. No second builder class. Existing three tools remain.
- [x] `[REQ-BUILD-011]`: Job/Phase parent. Goal mode uses CARD-099 no-tool planner for research phases. Research does not write `SKILL.md`.
- [x] `[REQ-BUILD-012]`: Approved commit writes `SKILL.md` through `UserSkillCatalog` into `$DATA_DIR/skills`. Same files Skills Studio edits. Draft/rejected fail closed.
- [x] `[REQ-BUILD-013]`: Soft sprawl / extend-specialist warning visible before commit. Not a hard gate.
- [x] `[REQ-BUILD-014]`: Packs are markdown + JSON stubs. No Python `BuiltinSkill` modules under `src/`.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Depends on CARD-106 drafts. No SkillOpt. No ACE. No LangGraph. No live Okta. No job-template YAML runner.
- Do not replace Conductor / Coding / Review.
- Spec: `docs/specs/agent-builder-hitl/`.