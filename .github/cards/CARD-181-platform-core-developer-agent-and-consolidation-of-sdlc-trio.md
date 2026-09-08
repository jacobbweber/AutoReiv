# [CARD-181] Platform Core Developer Agent and Consolidation of SDLC Trio

> **Status**: In Review
> **Created**: 2026-09-07
> **Spec Reference**: CARD-124; CARD-174; CARD-179
> **Labels**: `type:feature`, `type:architecture`, `AutoReiv.Agents`, `AutoReiv.PlatformPacks`

---

## 1. Why / Intent

In CARD-124, AutoReiv established an SDLC specialist trio (`conductor`, `coding`, `review`) that used multi-agent handoffs to manage software development.

While well-intentioned, the multi-agent handoff relay introduces significant practical drawbacks:
1. **Context Starvation & Nuance Loss**: Passing work through serialized handoff packets loses the rich conversation history and specific nuances Jacob discusses.
2. **High Latency & Slowness**: Running three separate agent turns with queue handoffs takes 3x to 5x longer for routine development tasks.
3. **Redundancy with Reflexion**: With automated self-verification (`ReflexionLoopEngine` / CARD-179), a single agent can already write code, run automated tests, inspect error traces, and self-correct without needing an external "Reviewer" agent persona.
4. **Platform First-Class Need**: Development is a core function of AutoReiv. Out of the box, users should have immediate software engineering capabilities without needing to manually import external packs.

This card consolidates the SDLC capability into a single, unified **Platform Core Developer** agent that executes the full engineering lifecycle in a continuous context window using **Goal Mode + Reflexion**.

---

## 2. Three Beats: How It Works

### Beat 1: The Platform Developer Agent
1. **What you see**: A first-class built-in agent named **Developer** in Chat and Agent Studio with a `[Platform]` badge. It is immediately available upon launching AutoReiv.
2. **What AutoReiv does now**: Platform agents are strictly `assistant` and `autoreiv`. Development required manually importing three separate packs from `agent-packs/`.
3. **What will change**: `platform-packs/developer/` ships with the repository and is automatically seeded into `$DATA_DIR/packs/developer/` on startup.

### Beat 2: Three Core Skills (Plan, Build, Test) with Multi-Language Shell
1. **What you see**: In Agent Studio, Developer shows three clear, everyday skills: `plan`, `build`, and `test`.
   - **`plan`**: Explores the codebase, reads project steering, checks backlog cards, and drafts technical specifications in `docs/specs/` and global ADRs in `docs/adr/`.
   - **`build`**: Implements code changes, edits files, and manages git commits.
   - **`test`**: Executes tests and linters across multiple languages (PowerShell Pester/PSScriptAnalyzer, Python pytest/ruff, etc.) using `cli_exec`, and verifies compliance with `verify_rtm.py`.
2. **What AutoReiv does now**: Tools were scattered across separate agents with limited language support.
3. **What will change**: Developer has a unified, general toolset (`read_project_file`, `write_project_file`, `cli_exec`, `execute_code`, git tools, card tools) driven by modular runbooks.

### Beat 3: Retiring the Conductor / Coding / Review Trio
1. **What you see**: A clean, uncluttered Agent Studio and Chat picker. The legacy trio is retired and replaced by Developer.
2. **What AutoReiv does now**: Three separate pack folders exist in `agent-packs/`.
3. **What will change**: The trio is archived/deprecated from the active catalog and hidden from chat pickers.

---

## 3. Technical Touchpoints

| Layer | Component | File Path |
| :--- | :--- | :--- |
| **Platform Seed** | Platform Pack Seed Registry | `src/infrastructure/skills/platform_packs.py` |
| **Pack Schema** | Platform Pack IDs & Constants | `src/application/agent_packs/schema.py` |
| **Pack Definition** | Shipped Developer Pack Manifest & Runbooks | `platform-packs/developer/pack.json`, `skills/plan/SKILL.md`, `skills/build/SKILL.md`, `skills/test/SKILL.md` |
| **Profiles & Roster** | Builtin Roster & Studio Registration | `src/domain/agents/profiles.py` |

---

## 4. Acceptance Criteria (Definition of Done)

- [x] [REQ-DEV-001] Author `platform-packs/developer` containing `pack.json` (Schema 1.1) and three modular skills: `plan`, `build`, and `test` with `SKILL.md` runbooks.
- [x] [REQ-DEV-002] Equip Developer with the unified engineering toolset: `read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, `git_status`, `git_diff`, `git_branch`, `git_commit`, `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_steering`, `read_spec`, `write_spec`.
- [x] [REQ-DEV-003] Add `"developer"` to `PLATFORM_PACK_IDS` in `src/infrastructure/skills/platform_packs.py` and `src/application/agent_packs/schema.py` so it is automatically seeded on startup.
- [x] [REQ-DEV-004] Update Agent Studio and Chat to display Developer with a `[Platform]` badge.
- [x] [REQ-DEV-005] Retire `conductor`, `coding`, and `review` from the active catalog and hide from chat pickers.
- [x] [REQ-DEV-006] All automated unit and integration tests pass cleanly via `pytest`.
- [x] [REQ-DEV-007] Zero lint errors via `ruff check .`.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Work strictly on local `qa` branch.
- No third-party product names in card or code.
- Information architecture: Cards track backlog/status; Specs (`docs/specs/`) hold permanent technical blueprints; ADRs (`docs/adr/`) hold global architectural decisions.
