# Requirements Specification: Control Plane Data Dir

> **Spec Status**: Draft
> **Target Release**: Slice B / control-plane data plane
> **Primary Component**: DATA / SKILLS / WEB
> **Hardware**: Local Ollama on Nimo (qwen3.8 / qwen3.6, context 131k-262k). VRAM is the constraint. Frontier providers must not be required.

---

## 1. Executive Summary & Intent

User data lives **outside the git checkout**, Hermes `~/.hermes` style. Live SQLite (jobs, custom agents, settings, sessions), PARA wiki, user `SKILL.md` packs, and future skill packs sit in one tree. The repo seeds builtins only. `AUTOREIV_DATA_DIR` is the env and the setting. Docker mounts that one tree.

Backup and Restore are one command / one UI action over that tree (zip or copy).

`DynamicSkillLoader` already parses agentskills.io `SKILL.md` but is unused at bootstrap. Slice B wires it for **USER** packs with progressive disclosure (list name+description; load body on demand) and must not break Python Builtin skills.

Skills Studio is a sibling of Agent Studio: browse/edit the same `SKILL.md` files a later Agent Builder will write. A playbook is SOP prose in `SKILL.md`. A job template is YAML for Job+Phases. They are different objects; job templates are stubbed as later cards.

This slice does **not** move the kernel, start Agent Builder specialist behavior, or start ACE/SkillOpt.

---

## 2. User Stories & EARS Functional Requirements

Every requirement uses EARS syntax and a unique identifier. DATA ids start at REQ-DATA-001.

### [REQ-DATA-001]: Resolve AUTOREIV_DATA_DIR

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL resolve the user data directory from AUTOREIV_DATA_DIR in this order: environment variable, then persisted setting, then the platform default outside the git checkout.`
- **Acceptance Criteria**:
  - [ ] Given no env and no setting, when the process starts on Windows, then the data dir is `%LOCALAPPDATA%\AutoReiv` (not the repo).
  - [ ] Given no env and no setting, when the process starts on POSIX, then the data dir is `~/.autoreiv`.
  - [ ] Given no env and no setting, when the process runs in Docker, then the data dir is `/data`.
  - [ ] Given `AUTOREIV_DATA_DIR` is set in the environment, when the process starts, then that path wins over a persisted setting.

### [REQ-DATA-002]: Data dir layout

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL keep live user state under the resolved data dir as autoreiv.db, wiki/, skills/, and reserved agents/ and templates/jobs/ directories.`
- **Acceptance Criteria**:
  - [ ] Given a resolved data dir, when the app starts, then SQLite (including jobs), wiki, and user skill packs resolve under that tree.
  - [ ] Given the git checkout, when Slice B ships, then it is not the live store for those artifacts.

### [REQ-DATA-003]: Derive legacy path overrides

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL derive the database path as $DATA_DIR/autoreiv.db and the wiki path as $DATA_DIR/wiki unless AUTOREIV_DB_PATH or AUTOREIV_WIKI_PATH are set explicitly, in which case the explicit path wins.`
- **Acceptance Criteria**:
  - [ ] Given only `AUTOREIV_DATA_DIR`, when bootstrap runs, then db and wiki are `$DATA_DIR/autoreiv.db` and `$DATA_DIR/wiki`.
  - [ ] Given `AUTOREIV_DB_PATH` is set, when bootstrap runs, then that db path is used.

### [REQ-DATA-004]: Migrate live checkout data without wipe

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the resolved data dir is missing the live database or wiki AND the previous live path still has those artifacts THE SYSTEM SHALL copy them into the data dir and THE SYSTEM SHALL NOT delete the source copies or create an empty replacement store.`
- **Acceptance Criteria**:
  - [ ] Given `./data/autoreiv.db` and `./data/wiki` exist (today's defaults) and the new dir lacks those files, when first boot after Slice B, then both are copied into the data dir and subsequent reads use the copies.
  - [ ] Given the destination already has `autoreiv.db`, when boot runs, then the checkout file is not copied over it.
  - [ ] Given migration runs, when it finishes, then the source copies still exist (copy, not move; no wipe).
  - [ ] Given `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` already point at live files, when those files are the source, then they are what get copied if the destination is empty.

### [REQ-DATA-005]: Repo seeds builtins only

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL treat repository Python skills and optional wiki or skill seed templates as builtins or seeds and SHALL write user-generated wiki, custom agents, jobs, and SKILL.md packs only into the data dir.`
- **Acceptance Criteria**:
  - [ ] Given a fresh data dir with no wiki, when first boot needs a vault, then the repo may seed a builtin welcome vault into `$DATA_DIR/wiki` and never the other way around.
  - [ ] Given a user edits a wiki note or saves a custom agent, when persisted, then the write lands in the data dir SQLite/wiki, not under `src/`.

### [REQ-DATA-006]: Docker single volume

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL default Docker to one volume mounted at AUTOREIV_DATA_DIR=/data covering the database, wiki, skills, and future packs.`
- **Acceptance Criteria**:
  - [ ] Given `docker-compose.yml`, when Slice B ships, then the two-file mounts of `./data/autoreiv.db` and `./data/wiki` are replaced by one tree mount.
  - [ ] Given a container restart, when `/data` persists, then jobs, wiki, custom agents, and user packs are still there.

### [REQ-DATA-007]: Backup the data dir

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the operator requests Backup THE SYSTEM SHALL produce a zip or copy of the entire resolved data dir as one CLI command and one Settings Studio action.`
- **Acceptance Criteria**:
  - [ ] Given a live data dir, when `autoreiv backup [dest]` or the Settings Backup control runs, then the archive or copy contains `autoreiv.db`, `wiki/`, `skills/`, and any other files in the tree.
  - [ ] Given the git checkout, when backup runs, then repo source is not included.
  - [ ] Backup is one command and one UI action. Not a multi-step export of db then wiki.

### [REQ-DATA-008]: Restore the data dir

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the operator confirms Restore of a backup zip or copy THE SYSTEM SHALL replace the resolved data dir with that tree and WHEN the operator cancels THE SYSTEM SHALL leave the live tree unchanged.`
- **Acceptance Criteria**:
  - [ ] Given a backup zip, when restore is confirmed, then the data dir matches the backup tree and the next boot uses it.
  - [ ] Given restore is not confirmed, when the operator cancels, then the live tree is unchanged.
  - [ ] Restore does not wipe the git checkout.
  - [ ] Restore is replace-the-tree, not a silent file-by-file merge.

### [REQ-DATA-009]: Mount user SKILL.md packs

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL scan $DATA_DIR/skills for agentskills.io SKILL.md packs at bootstrap using DynamicSkillLoader and SHALL keep Python Builtin skills registered exactly as BuiltinAgentRegistry.bootstrap does today.`
- **Acceptance Criteria**:
  - [ ] Given a valid pack at `$DATA_DIR/skills/<slug>/SKILL.md`, when bootstrap finishes, then that pack is listed as a user pack.
  - [ ] Given no user packs directory, when bootstrap runs, then Python builtins still register (today's set: Wiki, Weekly Notes, Sysadmin, System, Verification, Planning, Agent Builder, Orchestration, and the rest).
  - [ ] `DynamicSkillLoader` remains the parser. Python skill classes are not replaced by markdown.

### [REQ-DATA-010]: Progressive disclosure

- **Type**: State-Driven
- **EARS Statement**: `WHILE user packs are mounted THE SYSTEM SHALL expose only name and description in the catalog list and SHALL load the SKILL.md body and embedded tool JSON on demand.`
- **Acceptance Criteria**:
  - [ ] Given many user packs, when the catalog is listed, then only frontmatter name, description, and id/path are loaded, not full bodies.
  - [ ] Given an operator or agent needs a pack, when it is selected, allowlisted, or opened, then the body and tools are loaded via `DynamicSkillLoader.load_skill_from_markdown`.
  - [ ] `scan_skills_directory` today loads everything; Slice B adds a list-only path. Full load of one file stays valid on demand.

### [REQ-DATA-011]: Builtin name wins

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL keep a Python Builtin skill or tool when a user pack uses the same name and SHALL reject or suffix the user pack with an honest log.`
- **Acceptance Criteria**:
  - [ ] Given a user pack whose tool names collide with a builtin (for example WikiSkill), when mounted, then builtin tools remain and the user pack does not overwrite them.

### [REQ-DATA-012]: Skills Studio browse and edit

- **Type**: Event-Driven
- **EARS Statement**: `WHEN the operator opens Skills Studio THE SYSTEM SHALL list user packs from $DATA_DIR/skills and SHALL allow read and edit of each SKILL.md on disk.`
- **Acceptance Criteria**:
  - [ ] Given packs on disk, when Skills Studio loads, then each pack shows name and description.
  - [ ] Given an edit, when saved, then the file on disk is the source of truth (same files a later Agent Builder will write).
  - [ ] Skills Studio is a sibling tab of Agent Studio, not a panel inside Forge.

### [REQ-DATA-013]: Skills Studio lists tools in a pack

- **Type**: Event-Driven
- **EARS Statement**: `WHEN a pack is opened in Skills Studio THE SYSTEM SHALL list tools parsed from that SKILL.md.`
- **Acceptance Criteria**:
  - [ ] Given a `SKILL.md` with JSON tool blocks, when opened, then tool names and descriptions appear.
  - [ ] Given no tool blocks, when opened, then the tools list is empty (the pack may still be a playbook SOP).

### [REQ-DATA-014]: Job templates stubbed

- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL treat playbook SOP text in SKILL.md and job-template YAML as different objects and SHALL NOT implement job-template authoring in Slice B.`
- **Acceptance Criteria**:
  - [ ] Given Skills Studio, when the operator looks for job templates, then the UI may show an empty or later placeholder only.
  - [ ] Given `jobs.template_id`, when Slice B ships, then it stays nullable; no YAML runner is added.
  - [ ] Playbook = instructions in `SKILL.md`. Job template = later YAML for Job+Phases.

---

## 3. Non-Functional & Boundary Constraints

- **Hardware**: Primary runtime is local Ollama on Nimo (128GB unified). Slice B is filesystem and UI. It must not add LLM calls at bootstrap.
- **Concurrency**: Catalog list is metadata-only. Do not parse every `SKILL.md` body on startup.
- **Reliability**: Migration is copy, not move. Failed copy leaves the previous live paths readable and does not create an empty db that hides the old one.
- **Security**: Skills Studio and restore write only inside the resolved data dir. Path traversal out of `$DATA_DIR/skills` is rejected. Restore confirmation is required.
- **Backup**: Backup = zip or copy of the data dir tree. Not the git checkout.
- **Compatibility**: `AUTOREIV_DB_PATH` and `AUTOREIV_WIKI_PATH` remain explicit overrides. Existing `./data/` live files are migrated, not wiped.

---

## 4. Out of Scope

- Agent Builder specialist behavior (`propose_skill` / a specialist that writes packs).
- ACE playbook deltas.
- SkillOpt / nightly SkillOpt-Sleep.
- LangGraph (no graph runtime this epic).
- Moving or rewriting `AgentKernel`.
- Job-template YAML authoring and runner (later cards).
- Implementing CARD-014's DAG / Plan-and-Execute graph engine.
- Changing Job/Phase contracts from Slice A (CARD-096-101).

