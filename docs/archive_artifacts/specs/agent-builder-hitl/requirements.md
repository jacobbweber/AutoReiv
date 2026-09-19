# Requirements Specification: Agent Builder HITL

> **Spec Status**: Draft
> **Target Release**: Slice C / control-plane Agent Builder
> **Primary Component**: SKILLS / ORCHESTRATION / AGENTS
> **Hardware**: Local Ollama on Nimo (qwen3.8 / qwen3.6, context 131k-262k). VRAM is the constraint. Frontier providers must not be required.

---

## 1. Executive Summary & Intent

Slice A shipped durable Job/Phase and `propose_followup` HITL drafts. Slice B shipped `$DATA_DIR/skills` user packs and Skills Studio. Slice C opens **Agent Builder** as a user-facing specialist that talks to a human, researches, and emits **HITL drafts** for skills, tools, and workflows.

`AgentBuilderSkill` already exists (`src/application/skills/agent_builder_skill.py`, REQ-FORGE-005). It lists tools, proposes an in-memory agent blueprint, and persists custom **agent profiles** to SQLite. This slice **extends that class**. It does not invent a second builder.

`propose_skill` / `propose_tool` / `propose_workflow` reuse the CARD-101 `proposals` table (kinds `skill|tool|workflow` are already locked) and `pending_approvals`. They **never** auto-write `SKILL.md` or Python tools. Payload is what / why / how / where (`$DATA_DIR` path). A CARD-078 sprawl warning prefers more tools or skills on an existing specialist over a new agent when an allowlist would exceed ~12.

After a human Approves, Agent Builder may commit a pack into `$DATA_DIR/skills` through the same `UserSkillCatalog` files Skills Studio already reads and edits. User packs stay markdown + JSON. This slice does not write Python `BuiltinSkill` modules under `src/`.

The first homelab template is an **Okta admin** skill pack scaffold (playbook `SKILL.md` + JSON tool stubs). No live Okta API. No credentials. The user can open it in Skills Studio.

---

## 2. User Stories & EARS Functional Requirements

Every requirement uses EARS syntax and a unique identifier. BUILD ids start at REQ-BUILD-001.

### [REQ-BUILD-001]: propose_skill HITL draft

- **Type**: Event-Driven
- **EARS Statement**: `WHEN propose_skill is invoked THE SYSTEM SHALL persist a proposals row of kind skill with status draft and SHALL create a pending_approvals park and THE SYSTEM SHALL NOT write SKILL.md.`
- **Acceptance Criteria**:
  - [ ] Given a skill draft, when `propose_skill` runs, then a `proposals` row exists with `kind=skill` and `status=draft`.
  - [ ] Given that draft, when created, then a `pending_approvals` row exists for Chat HITL Approve/Reject.
  - [ ] Given that draft, when created, then no `SKILL.md` is created or modified under `$DATA_DIR/skills` or the git checkout.

### [REQ-BUILD-002]: propose_tool HITL draft

- **Type**: Event-Driven
- **EARS Statement**: `WHEN propose_tool is invoked THE SYSTEM SHALL persist a proposals row of kind tool with status draft and SHALL create a pending_approvals park and THE SYSTEM SHALL NOT write a Python tool module or SKILL.md.`
- **Acceptance Criteria**:
  - [ ] Given a tool draft, when `propose_tool` runs, then a `proposals` row exists with `kind=tool` and `status=draft`.
  - [ ] Given that draft, when created, then Chat HITL can Approve or Reject it.
  - [ ] Given that draft, when created, then no file under `src/application/skills/` is written and no pack JSON is committed to disk.

### [REQ-BUILD-003]: propose_workflow HITL draft

- **Type**: Event-Driven
- **EARS Statement**: `WHEN propose_workflow is invoked THE SYSTEM SHALL persist a proposals row of kind workflow with status draft and SHALL create a pending_approvals park and THE SYSTEM SHALL NOT auto-run a Job or write job-template YAML.`
- **Acceptance Criteria**:
  - [ ] Given a workflow draft, when `propose_workflow` runs, then a `proposals` row exists with `kind=workflow` and `status=draft`.
  - [ ] Given that draft, when created, then no phase starts and no `stream_turn` runs for the draft.
  - [ ] A workflow in this slice is a playbook SOP (ordered steps destined for `SKILL.md`). It is not job-template YAML and does not set `jobs.template_id`.

### [REQ-BUILD-004]: Draft payload is what / why / how / where

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL store each skill, tool, or workflow proposal payload with what, why, how, and where, where where is a path under the resolved data dir.`
- **Acceptance Criteria**:
  - [ ] Given a valid `propose_skill` / `propose_tool` / `propose_workflow` call, when persisted, then `payload_json` contains `what`, `why`, `how`, and `where`.
  - [ ] Given `where`, when validated, then it is jailed under `$DATA_DIR` (typically `$DATA_DIR/skills/<slug>/SKILL.md`). Path traversal is rejected.
  - [ ] Given a missing required payload field, when invoked, then the call fails closed and no proposal row is written.

### [REQ-BUILD-005]: Never auto-write SKILL.md or Python tools

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL NOT write SKILL.md, user-pack JSON, or Python BuiltinSkill modules as a side effect of creating or approving a skill, tool, or workflow proposal.`
- **Acceptance Criteria**:
  - [ ] Given `propose_*`, when it returns, then the filesystem under `$DATA_DIR/skills` and `src/` is unchanged.
  - [ ] Given HITL Approve on that proposal, when applied, then the proposal becomes `approved` and disk is still unchanged.
  - [ ] Given HITL Reject, when applied, then the proposal becomes `rejected` and disk is unchanged.
  - [ ] Disk write of a pack is CARD-107 `commit_skill_pack` (or Skills Studio save) after a human has approved.

### [REQ-BUILD-006]: Sprawl warning at allowlist ~12

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a proposal would grow an agent allowlist to 12 or more tools OR would create a new agent instead of extending an existing specialist THE SYSTEM SHALL emit a CARD-078-class warning and THE SYSTEM SHALL NOT block the draft.`
- **Acceptance Criteria**:
  - [ ] Given an existing specialist whose allowlist would become >= 12, when `propose_tool` or a new-agent path is drafted, then the proposal payload includes a sprawl warning that names the count and prefers adding tools/skills on that specialist over a new agent.
  - [ ] Given count < 12 and an existing specialist, when drafted, then no sprawl warning is required.
  - [ ] The warning does not block save or HITL Approve. Same threshold as Forge `FORGE_ALLOWLIST_WARN_AT = 12` (CARD-078). Tools count, not skill-pack count.

### [REQ-BUILD-007]: Reuse proposals table and pending_approvals

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist skill, tool, and workflow drafts in the existing proposals table and SHALL park them with the existing pending_approvals rows used by propose_followup.`
- **Acceptance Criteria**:
  - [ ] Given Slice C, when a draft is created, then it uses `ProposalKind.SKILL|TOOL|WORKFLOW` already locked in CARD-101. No second proposals table.
  - [ ] Given Chat HITL, when Approve/Reject is used, then the same `pending_approvals` + Chat HITL path handles these kinds. No new approval UI.
  - [ ] `followup_job` semantics from CARD-101 stay unchanged.

### [REQ-BUILD-008]: Approve does not write; reject discards

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a human Approves a skill, tool, or workflow proposal THE SYSTEM SHALL mark it approved without writing disk and WHEN a human Rejects it THE SYSTEM SHALL mark it rejected without writing disk.`
- **Acceptance Criteria**:
  - [ ] Given status `draft`, when Approve runs, then status is `approved` and no `UserSkillCatalog.save_pack` / file write occurs.
  - [ ] Given status `draft`, when Reject runs, then status is `rejected` and the draft is not committed.
  - [ ] Idempotent: a second Approve/Reject on an already-decided proposal does not rewrite disk.

### [REQ-BUILD-009]: Agent Builder is a user-facing specialist

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL expose Agent Builder as a builtin Chat specialist that talks to the human about skills, tools, and workflows and THE SYSTEM SHALL NOT make Agent Builder a second Conductor.`
- **Acceptance Criteria**:
  - [ ] Given the agent picker, when Slice C ships, then an `agent-builder` builtin profile is selectable in Chat.
  - [ ] Given Agent Builder, when compared to Conductor, then it does not write SDLC cards/specs and does not hand off Ready cards to Coding as its job.
  - [ ] Conductor, Coding, Review, Assistant, and AutoReiv keep their CARD-099+ roles.

### [REQ-BUILD-010]: Extend AgentBuilderSkill in place

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL register propose_skill, propose_tool, propose_workflow, and pack commit on the existing AgentBuilderSkill class and THE SYSTEM SHALL NOT add a second builder skill module.`
- **Acceptance Criteria**:
  - [ ] Given `src/application/skills/agent_builder_skill.py`, when Slice C ships, then the new tools live on `AgentBuilderSkill`.
  - [ ] There is no `AgentBuilderV2Skill`, `SkillPackBuilderSkill`, or parallel builder class.
  - [ ] Existing tools remain: `list_available_skills_and_tools`, `propose_agent_specification`, `save_agent_specification`. Custom agent profiles still persist to SQLite via that last tool; packs do not.

### [REQ-BUILD-011]: Job/Phase and no-tool planner for research

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the user chats with Agent Builder THE SYSTEM SHALL use Job/Phase as the parent of the goal and WHEN Goal mode is checked THE SYSTEM SHALL use the CARD-099 no-tool planner for linear research phases.`
- **Acceptance Criteria**:
  - [ ] Given Goal unchecked, when the user sends a message to Agent Builder, then CARD-099 default applies: one Job, one Phase, `stream_turn`.
  - [ ] Given Goal checked, when the planner runs, then it has no tools mounted and emits a linear research phase list (survey packs/specialists, draft playbook, declare tools, HITL propose). No DAG. No LangGraph.
  - [ ] Research phases do not write `SKILL.md`. Commit is a later step after HITL Approve.

### [REQ-BUILD-012]: Commit packs through Skills Studio files

- **Type**: Event-Driven
- **EARS Statement**: `WHEN Agent Builder commits an approved pack THE SYSTEM SHALL write SKILL.md through UserSkillCatalog into $DATA_DIR/skills and THE SYSTEM SHALL NOT write a second pack format.`
- **Acceptance Criteria**:
  - [ ] Given an approved skill/tool/workflow proposal, when `commit_skill_pack` (or equivalent) runs, then the file at `where` is a valid agentskills.io `SKILL.md` that Skills Studio can open.
  - [ ] Writes are jailed to `$DATA_DIR/skills`. Repo `.agents/skills` and `src/application/skills/` are not write targets.
  - [ ] Skills Studio save and Agent Builder commit are the same on-disk files (`render_skill_md` / `UserSkillCatalog.save_pack`).

### [REQ-BUILD-013]: Soft warnings before commit

- **Type**: Event-Driven
- **EARS Statement**: `WHEN Agent Builder is about to commit a pack THE SYSTEM SHALL surface sprawl and new-agent-vs-extend warnings to the human and THE SYSTEM SHALL NOT treat those warnings as a hard gate.`
- **Acceptance Criteria**:
  - [ ] Given allowlist would be >= 12 or a new agent is proposed instead of extending a specialist, when commit is requested, then the human sees the warning (Chat and/or proposal payload) before the write.
  - [ ] Given the human proceeds, when they confirm, then the write may proceed. Warnings are soft like CARD-078.
  - [ ] Given no sprawl condition, when commit runs, then no extra confirm is required beyond the HITL Approve already recorded.

### [REQ-BUILD-014]: User packs are markdown plus JSON, not Python modules

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist user packs as SKILL.md playbooks with optional fenced JSON tool stubs and THE SYSTEM SHALL NOT generate Python BuiltinSkill modules under src/ in this slice.`
- **Acceptance Criteria**:
  - [ ] Given a committed pack, when inspected, then it is frontmatter + SOP body + optional ```json tool blocks parsed by `DynamicSkillLoader`.
  - [ ] JSON tool stubs are not executed as Python (CARD-104 playbook handler stays).
  - [ ] A later card may add Python builtins; this slice does not.

### [REQ-BUILD-015]: Okta admin skill pack scaffold

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL seed a homelab Okta admin skill pack as a playbook SKILL.md under $DATA_DIR/skills that a user can open in Skills Studio.`
- **Acceptance Criteria**:
  - [ ] Given a fresh data dir (or missing dest), when Slice C seeds templates, then `$DATA_DIR/skills/okta-admin/SKILL.md` exists with agentskills.io name + description frontmatter and an Okta admin SOP body.
  - [ ] Given the dest already has that pack, when seed runs, then user edits are not overwritten.
  - [ ] Given Skills Studio, when the user opens `okta-admin`, then name, description, playbook, and declared tools are visible.

### [REQ-BUILD-016]: Okta tools are JSON stubs; no live API

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL declare Okta admin tools as JSON stubs inside the SKILL.md and THE SYSTEM SHALL NOT call the Okta API or require Okta credentials.`
- **Acceptance Criteria**:
  - [ ] Given the scaffold, when parsed, then at least one fenced JSON tool with `name` + `parameters` is listed (for example list users, reset/unlock, assign app).
  - [ ] Given those tools, when invoked, then they do not perform HTTP to Okta and do not read Okta API tokens.
  - [ ] No `.env` Okta keys are added in this slice.

---

## 3. Non-Functional & Boundary Constraints

- **Hardware**: Primary runtime is local Ollama on Nimo (128GB unified). Research uses the CARD-099 no-tool planner so it does not stampede VRAM. One named ReAct loop per phase.
- **Concurrency**: Global Ollama slot default 1 from Slice A stays. Agent Builder is not a parallel graph runtime.
- **Reliability**: Draft creation failing must not leave a half-written `SKILL.md`. Commit is a separate step after HITL.
- **Security**: `where` and commit paths are jailed to `$DATA_DIR/skills`. HITL parks stay parks. No live third-party credentials in the Okta scaffold.
- **Compatibility**: CARD-101 `followup_job` and Slice B Skills Studio / `DynamicSkillLoader` contracts stay. `ProposalKind` already includes `skill|tool|workflow`.
- **Sprawl**: Soft warning at 12 tools (CARD-078). Prefer extending an existing specialist.

---

## 4. Out of Scope

- SkillOpt / ACE nightly (SkillOpt-Sleep, playbook deltas).
- LangGraph (no graph runtime this epic).
- Training weights.
- Replacing Conductor (or Coding / Review SDLC).
- Live Okta credentials or Okta API integration.
- Job-template YAML authoring and runner (`jobs.template_id` stays nullable).
- Writing Python `BuiltinSkill` modules under `src/` for user packs.
- A second Agent Builder class or a second proposals/approvals table.
- Changing Slice A Job/Phase contracts or Slice B data-dir / Skills Studio contracts.
- Implementing CARD-014's DAG / Plan-and-Execute graph engine.
