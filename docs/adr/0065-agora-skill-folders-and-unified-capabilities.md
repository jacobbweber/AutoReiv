# [ADR-0065] Agora Skill Folders and Unified Capabilities

> **Status**: Accepted  
> **Date**: 2026-10-15  
> **Deciders**: Jacob Weber (Product Owner), coding assistant  
> **Related Cards**: [CARD-687](../../.agents/cards/CARD-687-agora-skill-folder-loader.md) (Slice 1: Agora folder loader), [CARD-688](../../.agents/cards/CARD-688-auto-scoped-session-skills.md) (Slice 2: Auto-scoped agents & session-mounted skill tools)  
> **Amends**: [ADR-0061](./0061-capability-scoping-skills-only-permission-one-enforcement-point.md) (skills also grant their colocated `tools/*.py`; `"*"` auto-scopes all non-hidden skills), [ADR-0062](./0062-agents-and-skills-are-files-no-packs.md) (skill folders contain `SKILL.md`, `references/`, and `tools/`), [ADR-0064](./0064-tools-load-all-at-once.md) (progressive disclosure via `skill_view` session mounting in Slice 2)  
> **Supersedes**: [ADR-0057](./0057-three-studios-and-developer-mediated-authoring.md) (merges Skill Studio and Tools Studio into one Capabilities tree studio in Slice 4)

---

## 1. Context & Problem Statement

In 1.0, adding or scoping a capability requires coordinating three separate primitives across three studios:
1. A runtime tool lives in `<data>/tools/<name>/tool.py` + `tool.json` (`RuntimeToolFiles`), built via a multi-hop `Ask Developer` -> `Toolsmith` chat turn and enabled in Tools Studio.
2. A skill lives in `platform/skills/<id>/SKILL.md` or `<data>/skills/<id>/SKILL.md` and binds tools by string ID in its `tools:` frontmatter, edited in Skill Studio.
3. An agent in `platform/agents/<id>.md` or `<data>/agents/<id>.md` must explicitly tick each skill ID in Agent Studio (`forge.js`) to receive those tools (`resolve_allowed_tools`).

While this kept permissions explicit, it placed a heavy hands-on tax on the operator to manually scope, wire, and approve every skill and tool across three UIs, while sending all ticked tool schemas on every turn (`ADR-0064`).

---

## 2. Decision Drivers

* **Zero boilerplate capability packaging**: A skill folder should be a self-contained unit (`SKILL.md` router + `references/*.md` deep docs + `tools/*.py` callables) without requiring separate `tool.json` files or manual `tools:` string lists.
* **Low context overhead via progressive disclosure**: Keep the base prompt small (a 1-line summary per skill folder) and load a skill's runbook, reference docs, and tools only when needed.
* **Hands-free self-extension with risk-based safety**: Allow agents to build and organize skill folders inline; pure (`read_only`, zero outside access) tools pass `ToolCheckService` and mount immediately, while tools touching network, files, or subprocesses ask via an inline approval gate or the Capabilities tree.
* **One Capabilities UI**: Replace the separate form-heavy Skill Studio and Tools Studio with a single Agora directory tree viewer where the operator can browse `skills/<id>/`, read/edit files, and toggle enablement.

---

## 3. Considered Options

* **Option 1 (Chosen): Agora Skill Folders + Dynamic `use_skill` + Unified Capabilities Tree**
  Consolidate skills, reference docs, and custom Python tools into `skills/<id>/` folders (`SKILL.md`, `references/`, `tools/*.py` with schemas inferred from `def run` type hints and docstrings), activate skills on demand via `use_skill`, support inline authoring/approval, and replace Skill Studio + Tools Studio with one Capabilities directory tree studio.
* **Option 2: Keep Split `skills/` and `tools/` Directories, Add Pre-Turn Sub-Call Router**
  Retain `<data>/tools/<name>/tool.json` and `SKILL.md` `tools:` lists, and add an out-of-context LLM sub-turn before each chat turn to rank and inject tools.
* **Option 3: Status Quo (`ADR-0061` + `ADR-0062` + `ADR-0064`)**
  Keep static per-agent skill ticks, separate `tools/` and `skills/` directories, and separate Skill/Tools studios.

---

## 4. Decision Outcome

Chosen option: **Option 1 (Agora Skill Folders + Dynamic `use_skill` + Unified Capabilities Tree)**, delivered in 4 slices under milestone **M26**:

### Slice 1 (`CARD-687`): Agora Skill Folder Loader (`SKILL.md` + `references/` + `tools/*.py`)
1. **Anatomy of a Skill Folder (`platform/skills/<id>/` and `<data>/skills/<id>/`)**:
   ```text
   skills/<id>/
   ├── SKILL.md                  # Entry point & overview (frontmatter + runbook)
   ├── references/               # On-demand reference markdown files (*.md)
   │   └── <topic>.md
   └── tools/                    # Colocated Python tools (*.py)
       └── <tool_name>.py        # Defines `def run(...)` with type hints & docstring
   ```
2. **Schema Inference from Python (`src/application/skills/agora_loader.py`)**:
   - Each `tools/<tool_name>.py` file defines a module-level `def run(...)`.
   - The tool name defaults to the file stem (`<tool_name>`).
   - The tool description is extracted from the module docstring or `run` docstring.
   - The JSON Schema `parameters` object is inferred via AST inspection from `def run`'s parameter names, type annotations (`str`, `int`, `float`, `bool`, `list`, `dict`, `Optional[...]`), and default values.
   - Optional module-level `RISK = "read_only" | "write" | "network" | "destructive"` sets the tool's risk tier (defaulting to `"read_only"` when `ToolCheckService.detect_access` finds zero outside access, or `"write"`/`"network"` when outside access is detected).
3. **Unified Skill Tool Resolution**:
   - `ContentStore.skill_tools(skill_ids)` returns the union of:
     a) Built-in/MCP tool IDs listed in the winning `SKILL.md`'s `tools:` frontmatter, and
     b) Enabled colocated tools discovered in `<skill_dir>/tools/*.py`.
   - `resolve_allowed_tools(agent)` (`src/application/agent_skills/allowed_tools.py`) remains the single permission decider (`ADR-0061`).
4. **Progressive Reference Reading**:
   - `skill_view(skill_id, reference=None)` returns `SKILL.md` plus the list of available `references/*.md` and colocated `tools/*.py`. Passing `reference="<topic>.md"` loads that specific reference document on demand without bloating the initial skill view.
5. **Tree Inspection API (`GET /api/capabilities/tree`)**:
   - Returns the structured Agora directory tree for all skills (`SKILL.md`, `references/`, `tools/` with inferred schema, `ToolCheckService` access report, and approval state) to back both testing and the Slice 4 Capabilities Studio.

### Slice 2 (`CARD-688`): Dynamic `skill_view` Session Mounting & Auto-Scoped Agents
- An agent with `"*"` in its `skills:` / `allowed_skill` list automatically discovers all non-hidden skills (`ticked_skills(agent)` expands `"*"` via `ContentStore().skills.list()`), while any explicitly listed skill IDs alongside `"*"` act as always-pinned skills (`pinned_skills(agent)`).
- For an `"*"` auto-scoped agent, `AgentKernel._resolve_active_tools` initially sends only `REQUIRED_PLATFORM_TOOLS`, `skill_view`, `list_user_skills`, and tools of `pinned_skills(agent)` so turns do not pay the schema token tax of every skill upfront.
- Calling `skill_view(skill_id)` in a session records `skill_id` as active for that session (in memory and in persisted transcript history) and refreshes the active tool list on the next ReAct step so that skill's enabled tools are immediately mounted and callable.

### Slice 3 (`CARD-689`): Inline Self-Building & Risk-Tiered Approval
- Agents and operators author or update `skills/<id>/` (`SKILL.md`, `references/*.md`, `tools/*.py`) directly via `save_skill_file` (`write_skill_file` tool in `capability-authoring` and `PUT /api/capabilities/skills/{skill_id}/file`).
- Pure `read_only` tools passing `ToolCheckService` with zero outside access (`check.status == "passed"`, `check.access == []`) auto-enable and mount immediately (`auto_enabled=True`), while tools with outside access (`network`, `files`, `programs`, `hidden_imports`) or non-`read_only` risk are saved disabled for operator approval.

### Slice 4: Unified Capabilities Studio
- Replaces `Skill Studio` (`skill_studio.js`) and `Tools Studio` (`tools_studio.js`) with a single **Capabilities** studio featuring an expandable Agora folder tree on the left and a file viewer/editor + enable/disable toggle on the right.

---

## 5. Guard Tests

* `tests/unit/architecture/test_card687_agora_skill_folders.py` (`pytest.mark.guard`): Verifies that colocated `tools/*.py` and `references/*.md` inside a skill folder are discovered via AST without executing untrusted top-level code, infer valid JSON Schema parameters from `def run(...)`, enforce `.approvals.json` SHA-256 gating for user-authored code, and flow through `resolve_allowed_tools(agent)`.
* `tests/unit/architecture/test_card688_auto_scoped_session_skills.py` (`pytest.mark.guard`): Verifies that `"*"` auto-scopes all non-hidden skills in `ticked_skills(agent)` and `resolve_allowed_tools(agent)`, keeps initial turn tool schemas lean (`REQUIRED_PLATFORM_TOOLS` + `skill_view` + `list_user_skills` + pinned skills), and dynamically mounts a skill's tools into `active_tools` as soon as `skill_view(skill_id)` is called in the session.
* `tests/unit/architecture/test_card689_agora_self_build_and_auto_enable.py` (`pytest.mark.guard`): Verifies that `save_skill_file` (`write_skill_file` and `PUT /api/capabilities/skills/{skill_id}/file`) runs `ToolCheckService` before writing `tools/<name>.py`, refuses broken/unsafe code, auto-enables and mounts pure `read_only` tools with zero outside access, and saves outside-access tools disabled (`approval="disabled"`).
