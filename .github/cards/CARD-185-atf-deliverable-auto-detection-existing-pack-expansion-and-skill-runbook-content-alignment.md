# [CARD-185] ATF Deliverable Auto-Detection Existing Pack Expansion and Skill Runbook Content Alignment

> **Status**: In Review
> **Created**: 2026-09-07
> **Spec Reference**: none
> **Labels**: `type:feature`, `agent-training-factory`, `mcp`

---

## 1. Why / Intent
When training an agent in the Agent Training Factory (ATF) with Deliverable Architecture set to **Auto**, the factory should recognize if the target agent already has an existing pack with an MCP server or native tools, and expand its capability coverage rather than guessing from scratch.

Furthermore, three key issues were discovered during live training runs:
1. **Skill Title & Content Bleed**: When multiple skills are authored in a run, every skill's `SKILL.md` was titled with the first skill's name (`# Hyper-V VM Lifecycle`), and the user's raw prompt was dumped verbatim into `## Purpose & Scope` and `### Objectives`, instead of writing clean procedural operational runbooks.
2. **Missing "Skill Only" Deliverable Support**: When the operator explicitly selects **"Procedural Skill Runbook Only"** (`skill`), the classifier ignored it and defaulted to MCP or native tools. The operator must be able to train pure procedural runbooks without tools.
3. **Pack Expansion & Visibility**: When re-training an agent with an existing MCP server, ATF authored all 4 tools in `mcp/server.py`, but the verify log only printed the first tool name, and no operator guidance was provided indicating the external Docker container needs rebuilding to load the expanded tools.

---

## 2. What to Build
- **Deliverable Classification & Existing Pack Detection (`src/application/agent_training_factory/phases/blueprint.py`)**:
  - Update `classify_deliverable_type` to recognize `"skill"` as a valid explicit deliverable architecture.
  - When deliverable is `"auto"`, inspect `packs/<agent_id>/pack.json` or agent profile: if an MCP server already exists, auto-classify as `"mcp"` to expand the server; if native tools exist, expand native tools.
  - When deliverable is `"skill"`, formulate skill specs with empty tools lists and author zero tool files.
- **Skill Title, Name & Runbook Content Alignment (`src/application/agent_training_factory/phases/author.py`)**:
  - In `AuthorPhase`, look up the matching skill spec for each `skill_id` (do not use `skill_specs[0]` for all skills).
  - Pass the exact skill `name` and domain `description` to `_format_standard_skill_runbook`.
  - In `_format_standard_skill_runbook`, generate domain-specific operational objectives instead of dumping raw user prompt paragraphs into `### Objectives`.
- **Author All-Tools Verification Logging (`src/application/agent_training_factory/phases/verify.py`)**:
  - Log and report all verified authored tool names in the verify battery result summary, not just `authored_tool_names[0]`.
- **MCP Container Rebuild Guidance (`src/application/agent_training_factory/phases/promote.py`)**:
  - When promoting an updated MCP server, include a container rebuild reminder in promotion notes: `docker build -t autoreiv-<slug>-mcp:latest packs/<slug>/mcp`.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] **AC-1**: When Deliverable Architecture is set to `"skill"`, ATF creates procedural `SKILL.md` runbooks and authors zero Python tools or MCP servers.
- [x] **AC-2**: When Deliverable Architecture is set to `"auto"`, ATF checks if the target agent pack already has an MCP server; if so, it maintains `"mcp"` architecture and augments the MCP server tools.
- [x] **AC-3**: Each authored skill in a multi-skill run receives its own distinct title, purpose, and operational objectives matching its skill ID and spec (no `# Hyper-V VM Lifecycle` title bleed across networking, template, or unattend skills).
- [x] **AC-4**: Raw user input prompt text is not dumped verbatim into `### Objectives` of authored `SKILL.md` runbooks.
- [x] **AC-5**: Verify battery logs all authored tools verified during testing.
- [x] **AC-6**: Automated unit tests pass via `pytest tests/unit/agent_training_factory/`.
- [x] **AC-7**: Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Working on branch `qa`.
- Card stays **Ready** until human visionary approves and says build.
- Follow AGENTS.md "How we walk cards with Jacob" (three beats: What he means, What AutoReiv does now, What will change).

