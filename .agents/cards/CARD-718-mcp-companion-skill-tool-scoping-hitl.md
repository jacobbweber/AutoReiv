---
id: CARD-718
title: "MCP Companion Skill Tool Scoping, HITL Auto-Run, and Capabilities Studio Copy"
type: bug
status: In Review
priority: P1
milestone: M31
needs_decision: none
proof:
  journeys: [card-718-mcp-companion-skill-tool-scoping-hitl]
  checks:
    - tests/unit/mcp/test_card718_mcp_companion_and_autorun.py
branch: feat/card-718-mcp-companion-skill-tool-scoping-hitl
log: {minutes: 35, qa_runs: 2, findings: 0}
created: 2026-10-18
---

# CARD-718 MCP Companion Skill Tool Scoping, HITL Auto-Run, and Capabilities Studio Copy

## Problem
When Jacob mounted and enabled his `GameDock` SSE MCP server on `AutoReiv` and asked in Chat (with Auto-run checked) to add the Steam game "Aska" to the GameDock catalog:
1. All 31 mounted `mcp_GameDock_*` tools showed `you_can_call: false` in `list_available_skills_and_tools`, so `AutoReiv` could not call `mcp_GameDock_get_add_game_guide` or `mcp_GameDock_add_catalog_entry`.
2. `AutoReiv` called both `write_skill_file` and `propose_skill` / `propose_tool`, and those HITL prompts ignored the Chat Auto-run checkbox (`approval_mode="run"`), parking for manual approval.
3. Seeing `you_can_call: false` and stale `"in Tools Studio"` strings in `register_native_tool`, `AutoReiv` told Jacob to enable the MCP server in "Tools Studio" (which was retired into Capabilities Studio) and tried to register a dummy native wrapper named `mcp_GameDock_add_catalog_entry`.
4. When `register_native_tool` rejected the `mcp_` prefix, `RcaProposalService` staged a false-positive `rca:tool:register_native_tool` repair proposal that prompted `AutoReiv` to "repair `register_native_tool`", creating a dummy `game_dock_add_catalog_entry` stub and overwriting `aska-gamedock-catalog/SKILL.md`.

## Cause
1. `resolve_allowed_tools(agent)` (`src/application/agent_skills/allowed_tools.py`) only grants tools listed in the YAML frontmatter `tools:` of the agent's ticked `SKILL.md` files (ADR-0061). However, `author_mcp_companion_skill` (`src/infrastructure/mcp/companion_author.py`) omitted `tools:` from the YAML frontmatter of `skills/mcp-<server>/SKILL.md`, and `save_agent_mcp_server` (`src/web/routers/agents.py`), `mount_agent_mcp_server`, and startup `lifespan` (`src/web/app.py`) never called `author_mcp_companion_skill` or ticked `mcp-<server>` on the agent.
2. `propose_skill_draft` (`src/application/orchestration/skill_proposals.py`) and `propose_tool_attachment` (`src/application/agent_skills/tool_attachment.py`) hardcoded `"auto_run": False` and created pending approvals without checking `get_tool_context().get("approval_mode") == "run"` or `resolve_approval_mode(store) == "hands_off"`. Additionally, `make_skill_write_guard` held back tools added to a user `SKILL.md` even when the agent already had permission to call those tools (`tool in resolve_allowed_tools(agent)`).
3. `src/application/skills/native_tool_engineering.py`, `src/application/tools/native_packaging.py`, `src/application/agent_skills/tool_attachment.py`, and `platform/skills/mcp-engineering/SKILL.md` still contained LLM-facing `"Tools Studio"` strings instead of `"Capabilities Studio"`.
4. `RcaProposalService.list_proposals` (`src/application/telemetry/rca_proposals.py`) staged `rca:tool:<name>` self-repair proposals for any failed tool span, including built-in platform tools rejecting invalid caller arguments.

## Change
1. **MCP Companion Skill & Agent Tool Scoping (`src/infrastructure/mcp/companion_author.py`, `src/web/mcp_mount_reconcile.py`, `src/web/routers/settings.py`, `src/web/routers/agents.py`, `src/web/app.py`, `src/application/skills/agora_authoring.py`):**
   - Update `author_mcp_companion_skill` to write the discovered `mcp_<server>_*` tool names (plus `mcp_<server>_*` wildcard) into the `tools:` YAML frontmatter of `$DATA_DIR/skills/mcp-<slug>/SKILL.md`.
   - Call `author_mcp_companion_skill` inside `reconcile_saved_mcp_server` (and startup `lifespan` / agent mount routes) whenever an enabled MCP server mounts tools, and tick `mcp-<slug>` on the target agent when saving/mounting an agent MCP server (removing the tick on delete).
   - In `save_skill_file` (`SKILL.md`) and `make_skill_write_guard`, extract any known `mcp_*` tools referenced in a user skill's markdown when `tools:` frontmatter is omitted, and do not hold back or park `attach_tool_to_skill` proposals for `mcp_*` tools the agent is already allowed to call (`tool in resolve_allowed_tools(agent)`).
2. **Honor Auto-Run on Proposal & Attachment Gates (`src/application/orchestration/skill_proposals.py`, `src/application/safety/approval_mode.py`, `src/application/agent_skills/tool_attachment.py`, `platform/skills/capability-authoring/SKILL.md`, `src/application/skills/agent_builder_tools.py`):**
   - Normalize `"run"` (Chat Auto-run checkbox) to `"hands_off"` in `normalize_approval_mode` and auto-approve `propose_skill` / `propose_tool` drafts (`status="approved"`, `auto_run=True`, approval resolved as `"approved"`) instead of parking a pending HITL card.
   - Clarify `capability-authoring/SKILL.md` so `AutoReiv` uses `write_skill_file` directly (without double-calling `propose_skill`) and calls mounted `mcp_<Server>_*` tools directly instead of writing a Python wrapper.
3. **Replace Stale "Tools Studio" LLM Strings (`src/application/skills/native_tool_engineering.py`, `src/application/tools/native_packaging.py`, `src/application/agent_skills/tool_attachment.py`, `platform/skills/mcp-engineering/SKILL.md`):**
   - Replace LLM-facing `"Tools Studio"` instructions and return messages with `"Capabilities Studio"`.
4. **Filter Built-In Tool Caller Errors Out of Telemetry RCA (`src/application/telemetry/rca_proposals.py`):**
   - Only stage `rca:tool:<name>` repair proposals for colocated Agora skill tools (`_locate_skill_tool`) or runtime-built native tools (`load_native_tool_names`), ignoring caller argument/validation rejections on built-in platform tools.

## What dies
- Stale `"Tools Studio"` instructions in `src/application/skills/native_tool_engineering.py`, `src/application/tools/native_packaging.py`, `src/application/agent_skills/tool_attachment.py`, and `platform/skills/mcp-engineering/SKILL.md`.
- Broken `/data/tools/game_dock_add_catalog_entry` dummy stub in the live container data volume (cleaned up on redeploy).

## Proof
- Journey `card-718-mcp-companion-skill-tool-scoping-hitl`:
  1. Attach and enable an MCP server (`GameDockQA`) via `/api/settings/mcp`, verify `skills/mcp-gamedockqa/SKILL.md` is authored with `tools:` frontmatter, and verify `autoreiv` ticks `mcp-gamedockqa` and gets `mcp_GameDockQA_*` tools.
  2. Open Capabilities Studio (`#view-capabilities`) and verify `mcp-gamedockqa` appears in `#capabilitiesTreeList` with `tools:` frontmatter and zero `"Tools Studio"` references.
  3. Save a user skill (`aska-gamedock-<viewport>`) referencing `mcp_GameDockQA_add_catalog_entry` and verify it retains the MCP tool in `tools:` with zero pending HITL approvals in `/api/hitl/pending` and zero built-in tool false-positives in `/api/telemetry/rca-proposals`.
- Checks:
  - `tests/unit/mcp/test_card718_mcp_companion_and_autorun.py`

## Plan and decisions
- **D1 (MCP tool scoping under ADR-0061):** Chosen Option 1 (Jacob approved): `author_mcp_companion_skill` writes `tools:` in the YAML frontmatter of `$DATA_DIR/skills/mcp-<server>/SKILL.md`, and saving/mounting an enabled MCP server authors the companion skill and ticks it on the agent so `resolve_allowed_tools(agent)` grants all `mcp_<Server>_*` tools immediately.
- **D2 (HITL Auto-run & skill authoring):** Chosen Option 1 (Jacob approved): `propose_skill`, `propose_tool`, and `normalize_approval_mode` honor `approval_mode="run"` (and `hands_off`), `make_skill_write_guard` does not hold back `mcp_*` tools the agent already has permission to call, and `capability-authoring` directs `AutoReiv` to `write_skill_file` without redundant `propose_*` or native wrapper calls.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-718-mcp-companion-skill-tool-scoping-hitl` | desktop | PASS | Mounted `GameDockQA` (2 tools), verified `mcp-gamedockqa` `tools:` frontmatter + `autoreiv` tick, verified Capabilities Studio tree, and verified `aska-gamedock-desktop` retained `mcp_GameDockQA_add_catalog_entry` with 0 pending HITL approvals and 0 RCA false-positives. |
| `card-718-mcp-companion-skill-tool-scoping-hitl` | phone | PASS | Same on phone (390×844) with zero horizontal overflow. |

Screenshots:
- `/tmp/autoreiv-qa/card-718/card-718-mcp-companion-skill-tool-scoping-hitl-desktop-01-mount-gamedockqa-stdio-mcp-server-and-verify-com.png`
- `/tmp/autoreiv-qa/card-718/card-718-mcp-companion-skill-tool-scoping-hitl-desktop-02-open-capabilities-studio-and-verify-mcp-gamedock.png`
- `/tmp/autoreiv-qa/card-718/card-718-mcp-companion-skill-tool-scoping-hitl-phone-02-open-capabilities-studio-and-verify-mcp-gamedock.png`

## Release note
- Enabled MCP servers now auto-author a companion `mcp-<server>` skill with `tools:` frontmatter and bind it to the agent so `mcp_<Server>_*` tools are immediately callable; proposal/attachment HITL gates honor the Chat Auto-run checkbox; LLM-facing tool messages reference Capabilities Studio instead of Tools Studio; and Telemetry RCA ignores caller validation errors on built-in platform tools.
