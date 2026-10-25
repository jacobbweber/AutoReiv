---
id: CARD-746
title: "Harden M34 live dogfooding for wiki CRUD mounting, skill tool invocation, and MCP engineering discovery"
type: bug
status: Done
priority: P1
milestone: M34
needs_decision: none
proof:
  journeys: [card-744-add-wiki-note-delete-and-move, card-743-harden-agora-skill-authoring-and-inline, card-745-docker-aware-mcp-engineering-and-host]
  checks: [tests/integration/test_card746_dogfood_m34_hardening.py]
branch: feat/card-746-harden-m34-live-dogfooding-for-wiki-crud
log: {minutes: 20, qa_runs: 1, findings: 5}
created: 2026-10-25
---

# CARD-746 Harden M34 live dogfooding for wiki CRUD mounting, skill tool invocation, and MCP engineering discovery

## Problem
When dogfooding M34 live on the running `autoreiv-control-plane` Docker container with natural prompts:
1. **Wiki move/delete**: Asking `AutoReiv` to create, move, and delete a wiki note in one natural prompt caused `AutoReiv` to call `wiki_note_create` and `wiki_note_update` repeatedly instead of `wiki_note_move` and `wiki_note_delete`.
2. **Skill/tool authoring & invocation**: Asking `AutoReiv` to create a skill/tool that inspects the wiki triggered `wiki_thin_grounding` (`is_wiki_create_ask=True`), causing `AutoReiv` to create a wiki note before authoring the skill; `AutoReiv` also wrote `Path(os.getenv("AUTOREIV_WIKI_PATH")) / "wiki"` and `sys.exit(1)` inside its tool because the sandbox contract was only in `references/authoring-guide.md`, and on the next turn thought it needed a `run_tool(...)` wrapper instead of calling `<tool_name>(...)` directly.
3. **MCP engineering discovery & user agent prompt reconciliation**: Asking `AutoReiv` to build and deploy a new Docker MCP server caused `AutoReiv` to open `skill_view("capability-authoring")` instead of `skill_view("mcp-engineering")` (and `/data/agents/autoreiv.md` still had a stale prompt body missing `mcp-engineering` and `wiki_note_move`), leaving `scaffold_mcp_server`, `test_mcp_server`, `deploy_mcp_container`, and `register_mcp_service` unmounted.

## Cause
1. `wiki-inbox` (`wiki_note_create`) and `wiki_tasks` (`wiki_note_update`) are pinned on `AutoReiv`, while `wiki_note_move` and `wiki_note_delete` were only listed on `wiki-curation` (an on-demand skill). Because 5 `wiki_note_*` tools were already mounted on Turn 1, the model assumed those were the only wiki tools and tried to fake move/delete via `wiki_note_update`.
2. `is_wiki_related_ask` and `is_wiki_create_ask` in `src/application/orchestration/wiki_thin_grounding.py` matched any prompt containing `"Create ... wiki"` even when the user asked to `"Create a new skill ... of my wiki"`. In addition, `ToolCheckService.check_native` did not reject `sys.exit(...)` in colocated tools, `capability-authoring/SKILL.md` did not inline the `AUTOREIV_WIKI_PATH` / direct tool-call rules, and `_decide_enable_skill_tool` in `src/web/routers/hitl.py` did not explicitly state that the enabled tool is called directly by name (`<tool_name>(...)`, not `run_tool`).
3. `UserSkillCatalog._activate_skill_for_session("capability-authoring")` did not co-activate `mcp-engineering` on agents that have `mcp-engineering` ticked, and `_reconcile_user_agent` in `src/infrastructure/content/store.py` did not treat missing `mcp-engineering` or `wiki_note_move` instructions in user `autoreiv.md` body as stale.

## Change
- `platform/skills/wiki-inbox/SKILL.md`, `src/application/skills/wiki_note_helpers.py`, `src/application/kernel/hitl_engine.py`, `src/application/orchestration/wiki_thin_grounding.py`, `src/application/capabilities/seeder.py`: include `wiki_note_move` and `wiki_note_delete` in `wiki-inbox` (so the full wiki note CRUD set is mounted together on Turn 1), register them in `DEFAULT_HIGH_RISK_TOOLS`, `_PROVENANCE_TOOLS`, and `CANONICAL_SYNONYMS`, and return a `note` hint on `create_wiki_note_impl` staging results explaining to call `wiki_note_move(source_path=..., destination_path=...)` to move notes into `01_Notes/`.
- `src/application/orchestration/wiki_thin_grounding.py`: exclude capability/skill/tool/MCP authoring and tool-run prompts (`create a new skill`, `colocated tool`, `mcp server`, `write_skill_file`, `scaffold_mcp_server`, `run <tool_name>`) from `is_wiki_related_ask` / `is_wiki_create_ask` so skill-authoring prompts that mention the wiki do not inject `WIKI GROUNDING CONSTRAINT` note-staging instructions.
- `src/application/tools/tool_check.py`, `platform/skills/capability-authoring/SKILL.md`, `src/web/routers/hitl.py`: reject `sys.exit()` / `exit()` in `ToolCheckService.check_native` static checks, inline the `AUTOREIV_WIKI_PATH` (do not append `/wiki`), top-level `RISK = "..."`, and direct `<tool_name>(...)` invocation rules into `capability-authoring/SKILL.md`, and update `_decide_enable_skill_tool` to explicitly instruct calling `<tool_name>(...)` directly.
- `src/application/skills/user_catalog.py`, `src/application/skills/session_skills.py`, `platform/agents/autoreiv.md`, `src/infrastructure/content/store.py`: co-activate `mcp-engineering` when `capability-authoring` is opened on an agent that allows `mcp-engineering`, document `wiki_note_move` and `wiki_note_delete` in `platform/agents/autoreiv.md`, and reconcile user `autoreiv.md` bodies missing `mcp-engineering` or `wiki_note_move`.

## What dies
- Nothing.

## Proof
- Journeys: `card-744-add-wiki-note-delete-and-move`, `card-743-harden-agora-skill-authoring-and-inline`, `card-745-docker-aware-mcp-engineering-and-host` plus live dogfooding of all 3 natural-prompt scenarios on `:8000`.
- Checks: `tests/integration/test_card746_dogfood_m34_hardening.py`.

## Plan and decisions
- Technical hardening discovered during live dogfooding requested by Jacob.

## Findings
- Fixed all 5 live dogfooding issues in-card.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-744-add-wiki-note-delete-and-move` | desktop | PASS | `/tmp/autoreiv-qa/card-746/card-744-add-wiki-note-delete-and-move/desktop/03-end.png` |
| `card-744-add-wiki-note-delete-and-move` | phone | PASS | `/tmp/autoreiv-qa/card-746/card-744-add-wiki-note-delete-and-move/phone/03-end.png` |

## Release note
- **Fixed**: Hardened M34 live dogfooding by mounting `wiki_note_move` and `wiki_note_delete` alongside `wiki_note_create`, excluding skill/MCP authoring prompts from `wiki_thin_grounding`, rejecting `sys.exit()` in colocated tools, co-activating `mcp-engineering` when `capability-authoring` is opened, and reconciling stale `autoreiv.md` prompt bodies (`CARD-746`).
