# Requirements: Platform Core Developer Agent [CARD-181]

## Overview
Consolidates the SDLC capability into a single, unified Platform Core Developer agent that executes the full engineering lifecycle in a continuous context window using Goal Mode + Reflexion.

## Requirements

### [REQ-DEV-001] Shipped Developer Agent Pack
- **User Story**: As a user launching AutoReiv, I want a built-in Developer agent so that I have immediate software engineering capabilities without importing external packs.
- **Acceptance Criteria**:
  - `platform-packs/developer/pack.json` exists conforming to Schema 1.1 with `id="developer"`, `name="Developer"`, and `show_in_chat=true`.
  - Developer includes three modular skills: `plan`, `build`, and `test` with runbooks under `skills/<skill_id>/SKILL.md`.

### [REQ-DEV-002] Unified Engineering Toolset
- **User Story**: As a developer instructing the Developer agent, I want it to read and edit files, run multi-language test suites, inspect git diffs, and manage cards so that it can autonomously complete features.
- **Acceptance Criteria**:
  - Developer's `pack_tool_names` includes `read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, `git_status`, `git_diff`, `git_branch`, `git_commit`, `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_steering`, `read_spec`, `write_spec`, and `propose_followup`.
  - `cli_exec` enables running multi-language test runners including PowerShell (Pester, PSScriptAnalyzer), Python (pytest, ruff), and TypeScript (vitest).

### [REQ-DEV-003] Platform Pack Seeding on Launch
- **User Story**: As a system administrator, I want Developer automatically seeded into `$DATA_DIR/packs/developer/` on startup so that it is always available.
- **Acceptance Criteria**:
  - `"developer"` is included in `PLATFORM_PACK_IDS` in `src/infrastructure/skills/platform_packs.py` and `src/application/agent_packs/schema.py`.
  - On launch, missing platform pack folders are copied into `$DATA_DIR/packs/` without overwriting existing user modifications.

### [REQ-DEV-004] Agent Studio & Chat Presentation
- **User Story**: As a user interacting with AutoReiv, I want Developer presented with a `[Platform]` badge in Chat and Agent Studio.
- **Acceptance Criteria**:
  - In Chat (`#agentSelect`) and Agent Studio (`#forgeAgentList`), Developer displays with `[Platform]` badge.
  - Developer shows in chat by default (`show_in_chat=true`).

### [REQ-DEV-005] Retirement of Legacy SDLC Trio
- **User Story**: As a user, I want the retired conductor, coding, and review personas removed from active pickers to eliminate confusion.
- **Acceptance Criteria**:
  - `conductor`, `coding`, and `review` are included in `CHAT_HIDDEN_BY_ID` and hidden from chat pickers.
  - Deprecated packs in `platform-packs/conductor/` are deleted.
