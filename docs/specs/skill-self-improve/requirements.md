# Requirements Specification: Skill Self-Improve

> **Spec Status**: Draft
> **Target Release**: Slice D / skill playbook self-improve
> **Primary Component**: SKILLS / ROUTINES / ORCHESTRATION
> **Hardware**: Local Ollama on Nimo (qwen3.8 / qwen3.6, context 131k-262k). VRAM is the constraint. Frontier providers must not be required. Operator timezone is America/New_York (Jacob).

---

## 1. Executive Summary & Intent

Slice C shipped Agent Builder HITL (`propose_skill` / `propose_tool` / `propose_workflow`), the `agent-builder` specialist, and the `okta-admin` seed pack under `$DATA_DIR/skills`. Slice D opens **skill self-improve**: playbooks get better from real execution without training weights, without rewriting tool Python mid-turn, and without a second graph runtime.

Two cadences, two cards, plus a curator:

1. **Online ACE-style playbook deltas (CARD-110).** After a turn, especially a failed one, AutoReiv records a *tiny* note from execution feedback. Conceptually Generator / Reflector / Curator (Agentic Context Engineering). Generator is the existing `AgentKernel` turn â€” do not add a second ReAct loop. Reflector extracts one small insight. Curator appends a delta (not a full `SKILL.md` rewrite). Snapshot before apply; rollback restores the snapshot. **Never rewrite tool Python mid-turn.** If the delta would change `SKILL.md`, it goes through CARD-106 `propose_skill` HITL so that gate holds. A sidecar append-only notes file is allowed; promoting those notes into `SKILL.md` still requires `propose_skill`.

2. **Nightly SkillOpt-Sleep-style eval (CARD-111).** A routine in the **existing** `routines` table harvests failed turns from telemetry / SQLite, optionally replays, runs a validation/checker gate, and stages a pack delta **only if the checker passes**. Shape matches Microsoft SkillOpt-Sleep (harvest â†’ mine â†’ replay optional â†’ consolidate â†’ held-out gate â†’ stage â†’ human adopt) implemented **in-process**. Do not vendor the Microsoft repo. Do not add a `skillopt` pip dependency unless a thin adapter is enough and still fails closed without it. **Weekday 02:00 "user-local 2am" is wrong** for Jacob (`America/New_York`). Prefer late-evening weekdays **21:00 America/New_York**, and **default the routine paused** (`enabled=false`) until the operator turns it on. Online ACE does not wait for this routine; this routine does not write mid-turn.

3. **Hermes curator (CARD-112).** Unused **user** packs that go stale are **archived** (move), never deleted. Bundled / `okta-admin` seed packs are never deleted and are not auto-archived without an explicit user action.

Non-goals stay non-goals: training weights, LangGraph, live tool codegen, SkillOpt as a required pip package, vendoring Microsoft/SkillOpt.

---

## 2. User Stories & EARS Functional Requirements

Every requirement uses EARS syntax and a unique identifier. IMPROVE ids start at REQ-IMPROVE-001.

### [REQ-IMPROVE-001]: Online ACE delta from execution feedback

- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent turn finishes with a named failure or checker miss THE SYSTEM SHALL record a tiny playbook delta note derived from that turn's feedback and THE SYSTEM SHALL NOT rewrite the entire SKILL.md in the same turn.`
- **Acceptance Criteria**:
  - [ ] Given a turn whose `telemetry_spans` row is `span_type=turn` with `success=false`, or a phase `react_state=FAILED`, or a CARD-099 checker that did not pass, when the turn ends, then at most one small delta note is produced (a bullet or short paragraph, not a full playbook rewrite).
  - [ ] Given a successful turn with no checker miss, when the turn ends, then no SKILL.md write is required. Optional success notes are still deltas, not rewrites.
  - [ ] Given that delta, when persisted, then the live `SKILL.md` body is unchanged in this turn unless a later CARD-106 HITL Approve + `commit_skill_pack` lands (CARD-110 uses propose, not commit, in-turn).

### [REQ-IMPROVE-002]: Generator / Reflector / Curator in-process

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL implement ACE Generator, Reflector, and Curator as in-process roles on the existing kernel and Agent Builder path and THE SYSTEM SHALL NOT add a second ReAct loop, LangGraph graph, or Microsoft ACE runtime.`
- **Acceptance Criteria**:
  - [ ] Generator is the existing `AgentKernel` `stream_turn` / `run_turn` trajectory. No second kernel.
  - [ ] Reflector is a post-turn hook or tool that reads that trajectory plus telemetry and emits a structured insight (what failed, what to try).
  - [ ] Curator merges the insight as an incremental item (append or HITL patch). It does not call an LLM to regenerate the whole playbook.
  - [ ] No import of an ACE GitHub repo. No new graph engine.

### [REQ-IMPROVE-003]: Never rewrite tool Python mid-turn

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL NOT create, modify, or delete Python tool modules or BuiltinSkill sources as a side effect of online ACE reflection or curation during a turn.`
- **Acceptance Criteria**:
  - [ ] Given online ACE, when Reflector or Curator runs, then no file under `src/` is written.
  - [ ] Given a delta that looks like a new Python builtin, when curated, then it stays a CARD-106 `propose_tool` draft with note `requires human/code card` (same as Slice C). It is not executed as Python.
  - [ ] JSON tool stubs in user packs remain stubs (CARD-104 / CARD-108). Online ACE does not "wire them up" live.

### [REQ-IMPROVE-004]: Snapshot before apply and rollback

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a playbook delta is about to be applied to SKILL.md or the notes sidecar THE SYSTEM SHALL write a snapshot of the current files and WHEN rollback is requested THE SYSTEM SHALL restore that snapshot.`
- **Acceptance Criteria**:
  - [ ] Given a pack under `$DATA_DIR/skills/<id>/`, when a snapshot is taken, then `SKILL.md` and any notes sidecar are copied under that pack's snapshot tree (for example `$DATA_DIR/skills/<id>/snapshots/<utc-iso>/`).
  - [ ] Given a snapshot, when rollback runs, then live `SKILL.md` / notes match the snapshot. Other packs are untouched.
  - [ ] Given snapshot I/O failure, when apply would proceed, then apply is skipped (fail closed). No half-written live pack.
  - [ ] Snapshots are data-dir files, not git commits. Do not `git commit` user packs.

### [REQ-IMPROVE-005]: SKILL.md patches use propose_skill HITL

- **Type**: Event-Driven
- **EARS Statement**: `WHEN an online ACE curator would change SKILL.md THE SYSTEM SHALL persist the change as a CARD-106 propose_skill draft and THE SYSTEM SHALL NOT write SKILL.md until a human Approves and a later commit_skill_pack runs.`
- **Acceptance Criteria**:
  - [ ] Given a curator delta targeting `SKILL.md`, when produced, then a `proposals` row `kind=skill` `status=draft` plus `pending_approvals` exists. Payload still has what / why / how / where, jailed under `$DATA_DIR/skills`.
  - [ ] Given that draft, when created, then live `SKILL.md` is unchanged (CARD-106 `[REQ-BUILD-001]` `[REQ-BUILD-005]` still hold).
  - [ ] Prefer `propose_skill` over a silent notes-only path whenever the intended durable artifact is the pack playbook. That is how the 106 gate holds.
  - [ ] Approve still does not write disk. Commit remains CARD-107 `commit_skill_pack`.

### [REQ-IMPROVE-006]: Append-only notes sidecar is allowed

- **Type**: Optional
- **EARS Statement**: `THE SYSTEM MAY append tiny ACE notes to a pack sidecar file without HITL and THE SYSTEM SHALL still require propose_skill before those notes are merged into SKILL.md.`
- **Acceptance Criteria**:
  - [ ] Given a sidecar (for example `$DATA_DIR/skills/<id>/PLAYBOOK_NOTES.md` or `notes.jsonl`), when a note is recorded, then the write is append-only. Existing lines are not rewritten or truncated.
  - [ ] Given that sidecar, when inspected, then `SKILL.md` is unchanged.
  - [ ] Given promotion of sidecar notes into `SKILL.md`, when requested, then the path is `propose_skill` (REQ-IMPROVE-005), not a direct save.
  - [ ] Sidecar lives under `$DATA_DIR/skills/<id>/`, not the git checkout.

### [REQ-IMPROVE-007]: Nightly eval is an AutoReiv routine

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL persist the SkillOpt-Sleep-shaped nightly skill eval as a row in the existing routines table and THE SYSTEM SHALL NOT add a second scheduler, cron daemon, or skillopt-sleep CLI requirement.`
- **Acceptance Criteria**:
  - [ ] Given Slice D, when seeded, then a routine id such as `skill-eval-sleep` exists in SQLite `routines` via `RoutineScheduler.seed_default_routines` / `BUILTIN_ROUTINES`.
  - [ ] Target agent is `agent-builder` (has `propose_skill`) or documents why another builtin is used. Not Coding. Not Review. Not Conductor.
  - [ ] Given that routine, when it fires, then `RoutineExecutor` + `routine_runs` record the run. Same scheduler tick as morning-briefing / nightly-hygiene.
  - [ ] No `skillopt-sleep schedule` OS cron. No Microsoft CLI.

### [REQ-IMPROVE-008]: Late-evening America/New_York, default paused

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL schedule the skill-eval routine for late-evening weekdays at 21:00 America/New_York and SHALL default it paused and THE SYSTEM SHALL NOT use 02:00 user-local as the default.`
- **Acceptance Criteria**:
  - [ ] Given the seeded routine, when inspected, then `enabled=false` (paused) until the operator enables it in Routines Studio / API.
  - [ ] Given `enabled=true`, when next run is computed, then it is weekday 21:00 in `America/New_York` (Monâ€“Fri). Not Saturday/Sunday unless the operator changes it.
  - [ ] Given timezone, when compared to UTC, then 21:00 ET is used (EDT UTC-4 or EST UTC-5), not 21:00 UTC and not 02:00 America/New_York.
  - [ ] `ScheduleMatcher` today evaluates due time in UTC and treats cron as a fallback interval. CARD-111 SHALL store a timezone-aware `next_run_at` (or equivalent) so 21:00 ET is real, or document the matcher change required. Do not silently treat `0 21 * * 1-5` as UTC.
  - [ ] Docs state the default is paused and why 02:00 is wrong for this operator.

### [REQ-IMPROVE-009]: Harvest failed turns from telemetry / SQLite

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the nightly skill-eval routine runs THE SYSTEM SHALL harvest failed turns from SQLite telemetry and job/phase state and THE SYSTEM SHALL NOT require an external transcript store.`
- **Acceptance Criteria**:
  - [ ] Given `telemetry_spans` (`span_type=turn`, `success=0` / false) and/or jobs/phases with `react_state=FAILED` inside a lookback window (default 24â€“72 hours, SkillOpt-Sleep harvest window is 72h), when harvest runs, then those rows are the candidate set.
  - [ ] Harvest is read-only on telemetry. It does not delete spans. It does not wipe either database.
  - [ ] Checkout `./data` is not the harvest source when the live data dir is `%LOCALAPPDATA%\AutoReiv` (CARD-109).
  - [ ] Lookback of 0 meaning "all history" is allowed as an operator override, bounded by a max-sessions / max-tasks cap so Nimo VRAM is not stampeded.

### [REQ-IMPROVE-010]: Replay is optional

- **Type**: Optional
- **EARS Statement**: `THE SYSTEM SHALL treat nightly replay of harvested tasks as optional and off by default and WHEN replay is enabled THE SYSTEM SHALL bound it so it cannot stampede the local Ollama slot.`
- **Acceptance Criteria**:
  - [ ] Given default config, when the routine runs, then harvest + mine + gate may run without replaying each failed turn through `stream_turn`.
  - [ ] Given replay enabled, when it runs, then it uses the existing kernel / Job-Phase path, honors `max_concurrent_generations` (CARD-098 default 1), and does not open a LangGraph.
  - [ ] Dream rollouts / synthetic variants (SkillOpt `dream_rollouts`, `recall_k`) are out of scope unless they fit the optional replay flag without a pip dependency.

### [REQ-IMPROVE-011]: Validation gate; apply only if checker passes

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the nightly routine proposes a skill delta THE SYSTEM SHALL run a validation checker and THE SYSTEM SHALL NOT stage or apply the delta if the checker does not pass.`
- **Acceptance Criteria**:
  - [ ] Given harvested items, when a candidate SKILL.md patch is produced, then a named checker runs (reuse CARD-099 Verify / `VerificationSkill` / honest skip â€” a missing checker is not `verification_passed`).
  - [ ] Given checker pass, when staging, then the delta is a CARD-106 `propose_skill` draft (HITL). Auto-adopt / auto-`commit_skill_pack` is off by default (SkillOpt-Sleep stages for review; AutoReiv already has Approve).
  - [ ] Given checker fail or skip, when staging would happen, then no proposal row is written and live `SKILL.md` is unchanged. Routine run records the skip/fail in `routine_runs`.
  - [ ] Gate is in-process. Do not require Microsoft's vendored gate.

### [REQ-IMPROVE-012]: In-process SkillOpt/ACE patterns; no required pip

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL implement ACE and SkillOpt-Sleep patterns in-process and THE SYSTEM SHALL NOT require the skillopt package, a clone of microsoft/SkillOpt, or training of model weights.`
- **Acceptance Criteria**:
  - [ ] `pyproject.toml` / Windows launcher do not add `skillopt` as a required dependency.
  - [ ] A thin optional adapter is allowed only if the product still runs when the extra is absent (import fail closed, routine records skip).
  - [ ] No weight training, no LoRA, no epoch loop against a frontier trainer.
  - [ ] Nightly is separate from online ACE. Online does not block on the routine. The routine does not mutate packs mid-user-turn.

### [REQ-IMPROVE-013]: Hermes curator archives stale unused user packs

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a user skill pack is unused past the stale window THE SYSTEM SHALL archive it by moving it out of the live skills tree and THE SYSTEM SHALL NOT delete the pack.`
- **Acceptance Criteria**:
  - [ ] Given a pack with `origin=user` that has not been listed as used (no `skill_view`, no pack tool invoke, no Skills Studio open/save) for the stale window (default 30 days, configurable), when curator runs, then the pack directory is moved to an archive tree under `$DATA_DIR` (for example `$DATA_DIR/skills/_archive/<id>/` or `$DATA_DIR/skills-archive/<id>/`).
  - [ ] Given that move, when `GET /api/skills/user-packs` runs, then the archived pack is not in the live list (or is listed with `origin=archived` only if the API explicitly supports an include-archived flag; default list is live packs).
  - [ ] Live `SKILL.md` is not deleted. Archive is a rename/move of the directory.
  - [ ] Curator may run as part of the nightly routine or a sibling routine; it still uses the existing routines table if scheduled.

### [REQ-IMPROVE-014]: Never delete bundled or okta-admin seed without the user

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL NOT delete or auto-archive bundled seed packs including okta-admin without an explicit user action and THE SYSTEM SHALL NOT delete repo seed sources.`
- **Acceptance Criteria**:
  - [ ] Given pack id `okta-admin` or any id in `BUNDLED_PACK_IDS` (`src/infrastructure/skills/seed.py`), when curator runs, then the live dest is left in place. No move. No delete.
  - [ ] Given `src/infrastructure/skills/seeds/okta-admin/SKILL.md`, when curator runs, then that repo file is never deleted or overwritten.
  - [ ] Given an operator wants to archive `okta-admin`, when requested, then it requires an explicit user confirm (Chat HITL or Settings). Default curator never proposes that delete.
  - [ ] Copy-if-missing seed (CARD-108) still does not overwrite dest.

### [REQ-IMPROVE-015]: Archive is reversible

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the user unarchives a pack THE SYSTEM SHALL move it back into $DATA_DIR/skills and THE SYSTEM SHALL NOT require re-seeding from git.`
- **Acceptance Criteria**:
  - [ ] Given an archived pack directory, when unarchive runs, then it returns to `$DATA_DIR/skills/<id>/` and Skills Studio / `GET /api/skills/user-packs` can open it.
  - [ ] Given dest already exists, when unarchive would clobber, then fail closed. No silent overwrite.
  - [ ] Unarchive does not run `commit_skill_pack` and does not create a new proposal.

### [REQ-IMPROVE-016]: Online and nightly stay separate

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL keep online ACE deltas and the nightly skill-eval routine as separate paths and THE SYSTEM SHALL NOT block a chat turn on the nightly job.`
- **Acceptance Criteria**:
  - [ ] Online ACE (CARD-110) may run at end of a user turn. It does not enqueue the nightly routine.
  - [ ] Nightly (CARD-111) does not attach to `stream_turn` as a child phase.
  - [ ] Curator (CARD-112) may be invoked by the nightly routine but does not rewrite packs during an interactive turn.

---

## 3. Non-Functional & Boundary Constraints

- **Hardware**: Primary runtime is local Ollama on Nimo (128GB unified). Nightly harvest is SQLite reads. Optional replay honors CARD-098 generation semaphore default 1. Online Reflector must be cheap (no extra multi-agent graph).
- **Timezone**: Operator is America/New_York. Routines due-time math must not assume UTC clock hours equal local hours. Default paused avoids surprise 2am GPU load.
- **Concurrency**: Global Ollama slot default 1 stays. Nightly must not start if a chat turn holds the slot, or it must queue.
- **Reliability**: Snapshot before any pack apply. Fail closed. Do not wipe `autoreiv.db` or checkout `./data`. CARD-109 data dir (`%LOCALAPPDATA%\AutoReiv`) is the live tree.
- **Security**: Pack paths jailed under `$DATA_DIR/skills`. HITL parks stay parks. Harvested telemetry may contain user text; do not ship it to a frontier provider as a required path. Optional SkillOpt adapter, if any, is off by default.
- **Compatibility**: CARD-106 propose/approve/reject contracts stay. CARD-107 commit stays the only pack write from Agent Builder. CARD-108 okta-admin seed stays copy-if-missing. CARD-102/109 data dir stays.
- **Sprawl**: Soft warning at 12 tools (CARD-078) still applies if a nightly draft would grow an allowlist.

---

## 4. Out of Scope

- Training weights, LoRA, DPO, or any optimizer that writes model files.
- LangGraph or any DAG / Plan-and-Execute graph engine (CARD-014 stays later).
- Live tool codegen (writing Python `BuiltinSkill` modules under `src/` from a turn or nightly job).
- Required `skillopt` / `skillopt-sleep` pip dependency, clone, or vendor of microsoft/SkillOpt. Thin optional adapter only.
- Auto-adopt / auto-commit of SKILL.md (SkillOpt `--auto-adopt` is off; AutoReiv HITL is the adopt step).
- Default schedule of 02:00 local or "whenever weekday night in UTC".
- Deleting user packs or bundled seeds.
- Replacing Conductor, Coding, Review, or Agent Builder.
- Changing Slice A Job/Phase or Slice B Skills Studio contracts except to list archived packs.
- Wiping or merging checkout `./data` and LocalAppData databases (CARD-109).
