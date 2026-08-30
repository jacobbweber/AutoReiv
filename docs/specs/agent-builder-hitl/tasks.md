# Implementation Tasks: Agent Builder HITL

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)
> **Traceability Key**: All tasks must reference their corresponding `[REQ-xxx]` tags.
> **Cards**: CARD-106 through CARD-108. One card per vertical slice. No feature code in the spec-open commit.

---

## Vertical Slice Breakdown

### Slice C1 -- CARD-106 propose_skill / propose_tool / propose_workflow HITL drafts

- [ ] **Task 1.1** `[REQ-BUILD-001]` `[REQ-BUILD-002]` `[REQ-BUILD-003]` `[REQ-BUILD-007]`: [RED] Failing tests that `propose_skill` / `propose_tool` / `propose_workflow` write `proposals` rows (`kind` skill|tool|workflow, `status` draft) plus `pending_approvals`, using the CARD-101 table. No second proposals store.
- [ ] **Task 1.2** `[REQ-BUILD-001]` `[REQ-BUILD-002]` `[REQ-BUILD-003]` `[REQ-BUILD-007]`: [GREEN] Tools registered on existing `AgentBuilderSkill`. Helper may mirror `followup.py`. `followup_job` behavior unchanged.
- [ ] **Task 1.3** `[REQ-BUILD-004]`: [RED] Payload requires what / why / how / where. `where` jailed under `$DATA_DIR`. Missing field fails closed with no row.
- [ ] **Task 1.4** `[REQ-BUILD-004]`: [GREEN] Persist those four fields. Traversal rejected.
- [ ] **Task 1.5** `[REQ-BUILD-005]` `[REQ-BUILD-008]`: [RED] Propose, Approve, and Reject leave `$DATA_DIR/skills` and `src/application/skills/` unchanged. Approve does not `save_pack`. Reject does not write.
- [ ] **Task 1.6** `[REQ-BUILD-005]` `[REQ-BUILD-008]`: [GREEN] Decision helper honors skill|tool|workflow. No Job auto-run. Workflow is playbook SOP, not job-template YAML.
- [ ] **Task 1.7** `[REQ-BUILD-006]`: [RED] When target allowlist would be >= 12, or a new agent is preferred over extending a specialist, payload includes a CARD-078 warning. Count < 12 needs no warning. Warning does not block the draft.
- [ ] **Task 1.8** `[REQ-BUILD-006]`: [GREEN] Soft warning. Same threshold 12. Prefer existing specialist.

### Slice C2 -- CARD-107 Agent Builder specialist + Job/Phase + data_dir skills

- [ ] **Task 2.1** `[REQ-BUILD-009]`: [RED] Builtin `agent-builder` profile is selectable in Chat. It is not Conductor (no SDLC card/spec authorship as its job).
- [ ] **Task 2.2** `[REQ-BUILD-009]`: [GREEN] Profile in `BUILTIN_PROFILES`. Allowlist stays under 12. Coding/Review/Conductor do not get `propose_skill`.
- [ ] **Task 2.3** `[REQ-BUILD-010]`: [RED] New tools live on `AgentBuilderSkill`. No second builder class.
- [ ] **Task 2.4** `[REQ-BUILD-010]`: [GREEN] Keep `list_available_skills_and_tools`, `propose_agent_specification`, `save_agent_specification`. Packs are additional tools, not a replacement module.
- [ ] **Task 2.5** `[REQ-BUILD-011]`: [RED] Default Chat with Agent Builder is one Job + one Phase + `stream_turn`. Goal mode uses CARD-099 no-tool linear planner for research phases. Research phases do not write `SKILL.md`.
- [ ] **Task 2.6** `[REQ-BUILD-011]`: [GREEN] Reuse Job/Phase orchestrator. No LangGraph. No second planner.
- [ ] **Task 2.7** `[REQ-BUILD-012]` `[REQ-BUILD-014]`: [RED] `commit_skill_pack` on an approved proposal writes agentskills.io `SKILL.md` via `UserSkillCatalog` under `$DATA_DIR/skills`. Draft/rejected fail closed. JSON tools are stubs, not Python modules under `src/`.
- [ ] **Task 2.8** `[REQ-BUILD-012]` `[REQ-BUILD-014]`: [GREEN] Same files Skills Studio opens. Jail to skills tree.
- [ ] **Task 2.9** `[REQ-BUILD-013]`: [RED] Soft sprawl / extend-specialist warning is visible before commit. Not a hard gate.
- [ ] **Task 2.10** `[REQ-BUILD-013]`: [GREEN] CARD-078-class warning in tool result and/or HITL arguments.

### Slice C3 -- CARD-108 Okta skill pack template (scaffold only)

- [ ] **Task 3.1** `[REQ-BUILD-015]`: [RED] Copy-if-missing seeds `$DATA_DIR/skills/okta-admin/SKILL.md` with name + description frontmatter and an Okta admin SOP body. Existing dest is not overwritten. Skills Studio can open it.
- [ ] **Task 3.2** `[REQ-BUILD-015]`: [GREEN] Repo seed copied at bootstrap or catalog init.
- [ ] **Task 3.3** `[REQ-BUILD-016]`: [RED] Pack declares JSON tool stubs (`name` + `parameters`) such as list users, reset/unlock, assign app. Invoking them does not HTTP to Okta and does not require credentials.
- [ ] **Task 3.4** `[REQ-BUILD-016]`: [GREEN] Stubs only. No Okta env keys. CARD-104 playbook handler remains.

### Slice C4 -- Verification, traceability, QA handoff

- [ ] **Task 4.1**: pytest + ruff on touched Python.
- [ ] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [ ] **Task 4.3**: Human QA on Jarvis/Nimo: Agent Builder in picker; `propose_skill` parks HITL and writes no file; Approve still writes no file; commit lands a pack Skills Studio can open; Okta scaffold opens with stub tools; no Okta credentials; Conductor still does cards. Do not push.

---

## Explicitly not in these tasks

SkillOpt, ACE nightly, LangGraph, training weights, replacing Conductor, live Okta API/credentials, job-template YAML runner, Python BuiltinSkill modules under `src/` for user packs, a second builder class, a second proposals table, Slice A Job/Phase contract changes, Slice B Skills Studio contract changes, CARD-014 DAG.
