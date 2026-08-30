# Implementation Tasks: Control Plane Data Dir

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)
> **Traceability Key**: All tasks must reference their corresponding `[REQ-xxx]` tags.
> **Cards**: CARD-102 through CARD-105. One card per vertical slice. No feature code in the spec-open commit.

---

## Vertical Slice Breakdown

### Slice B1 -- CARD-102 User data directory

- [ ] **Task 1.1** `[REQ-DATA-001]` `[REQ-DATA-002]` `[REQ-DATA-003]`: [RED] Failing tests that AUTOREIV_DATA_DIR resolves env > setting > platform default, layout is db/wiki/skills plus reserved agents/ and templates/jobs/, and db/wiki derive unless explicit AUTOREIV_DB_PATH / AUTOREIV_WIKI_PATH win.
- [ ] **Task 1.2** `[REQ-DATA-001]` `[REQ-DATA-002]` `[REQ-DATA-003]`: [GREEN] DataDirResolver. Windows `%LOCALAPPDATA%\AutoReiv`, POSIX `~/.autoreiv`, Docker `/data`.
- [ ] **Task 1.3** `[REQ-DATA-004]`: [RED] First boot copies live `./data/autoreiv.db` and `./data/wiki` into an empty dest. Does not overwrite dest. Does not delete source. Failed copy does not open an empty dest db as live.
- [ ] **Task 1.4** `[REQ-DATA-004]`: [GREEN] Copy migrate, no wipe.
- [ ] **Task 1.5** `[REQ-DATA-005]` `[REQ-DATA-006]`: [RED] User writes land in the data dir. docker-compose is one volume at `/data`. Repo seeds builtins/welcome vault only.
- [ ] **Task 1.6** `[REQ-DATA-005]` `[REQ-DATA-006]`: [GREEN] Wire app.py, CLI `--data-dir`, `.env.example`, compose. Every wiki/db consumer uses resolved paths.

### Slice B2 -- CARD-103 Backup and Restore

- [ ] **Task 2.1** `[REQ-DATA-007]`: [RED] One CLI command and one Settings action zip or copy the entire data dir. Checkout source is not in the archive.
- [ ] **Task 2.2** `[REQ-DATA-007]`: [GREEN] `autoreiv backup` + Settings "Backup data dir".
- [ ] **Task 2.3** `[REQ-DATA-008]`: [RED] Restore with confirm replaces the tree. Cancel leaves live tree. Zip missing db is rejected. No silent merge.
- [ ] **Task 2.4** `[REQ-DATA-008]`: [GREEN] `autoreiv restore --yes` + Settings Restore.

### Slice B3 -- CARD-104 Mount user agentskills.io packs

- [ ] **Task 3.1** `[REQ-DATA-009]`: [RED] Bootstrap scans `$DATA_DIR/skills/**/SKILL.md` via DynamicSkillLoader. Missing skills dir still registers today's Python builtins.
- [ ] **Task 3.2** `[REQ-DATA-009]`: [GREEN] Wire loader for USER packs only. Do not replace Python skill classes.
- [ ] **Task 3.3** `[REQ-DATA-010]`: [RED] Catalog list is name+description+path only. Body and tool JSON load on demand.
- [ ] **Task 3.4** `[REQ-DATA-010]`: [GREEN] Frontmatter-only list path on DynamicSkillLoader (or thin wrapper). Full `load_skill_from_markdown` on demand.
- [ ] **Task 3.5** `[REQ-DATA-011]`: [RED] Colliding user tool name does not overwrite a Python builtin.
- [ ] **Task 3.6** `[REQ-DATA-011]`: [GREEN] Builtin wins; honest log.

### Slice B4 -- CARD-105 Skills Studio UI

- [ ] **Task 4.1** `[REQ-DATA-012]`: [RED] Sibling tab of Agent Studio lists user packs from `$DATA_DIR/skills` and reads/edits SKILL.md on disk.
- [ ] **Task 4.2** `[REQ-DATA-012]`: [GREEN] Skills Studio tab + jailed API. Same files a later Agent Builder will write.
- [ ] **Task 4.3** `[REQ-DATA-013]`: [RED] Opening a pack lists tools parsed from that SKILL.md. No tool blocks => empty list.
- [ ] **Task 4.4** `[REQ-DATA-013]`: [GREEN] Tools list in the pack pane.
- [ ] **Task 4.5** `[REQ-DATA-014]`: [RED] Job templates are an empty/later placeholder. Playbook SOP is the SKILL.md body. No YAML runner.
- [ ] **Task 4.6** `[REQ-DATA-014]`: [GREEN] Stub only. Do not author job templates.

### Slice B5 -- Verification, traceability, QA handoff

- [ ] **Task 5.1**: pytest + ruff on touched Python. Frontend unit/smoke if Skills Studio ships.
- [ ] **Task 5.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [ ] **Task 5.3**: Human QA on Jarvis/Nimo: default data dir outside the repo; live `./data` db+wiki copied not wiped; backup zip then restore; drop a SKILL.md pack and see it listed without losing Wiki tools; edit the pack in Skills Studio. Do not push.

---

## Explicitly not in these tasks

Agent Builder specialist behavior, ACE, SkillOpt, LangGraph, moving AgentKernel, job-template YAML authoring/runner, CARD-014 DAG, Slice A Job/Phase contract changes.


### Slice B6 -- CARD-113 Skills Studio archive and confirm-delete

- [x] **Task 6.1** `[REQ-DATA-015]` `[REQ-DATA-016]`: [RED] Archive hides from live list; unarchive restores; Studio lists user packs only.
- [x] **Task 6.2** `[REQ-DATA-015]` `[REQ-DATA-016]`: [GREEN] Wire CARD-112 archive/unarchive/archived-packs into Skills Studio with confirm.
- [x] **Task 6.3** `[REQ-DATA-017]` `[REQ-DATA-018]`: [RED] DELETE without confirm 400; DELETE user pack removes dir; DELETE okta-admin without confirm_seed 409 and files remain; jail cannot delete `../`.
- [x] **Task 6.4** `[REQ-DATA-017]` `[REQ-DATA-018]`: [GREEN] `DELETE /api/skills/user-packs/{id}` jailed hard-delete with confirm / confirm_seed. UI Archive / Unarchive / Delete.
- [x] **Task 6.5**: String test that skills.js / index has archive/delete and does not present builtin python tool names as packs. pytest + ruff. CHANGELOG Unreleased.

