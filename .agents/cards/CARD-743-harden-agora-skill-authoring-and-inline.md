---
id: CARD-743
title: "Harden Agora skill and tool self-authoring with on-demand mounting, AST import/signature validation, and inline chat approval"
type: bug
status: In Review
priority: P1
milestone: M34
needs_decision: none
proof:
  journeys: [card-743-harden-agora-skill-authoring-and-inline]
  checks: [tests/integration/test_card689_agora_self_build_contract.py, tests/unit/architecture/test_card689_agora_self_build_and_auto_enable.py, tests/unit/tools/test_tool_check.py]
branch: feat/card-743-harden-agora-skill-authoring-and-inline
log: {minutes: 30, qa_runs: 2, findings: 1}
created: 2026-10-24
---

# CARD-743 Harden Agora skill and tool self-authoring with on-demand mounting, AST import/signature validation, and inline chat approval

## Problem
In live dogfooding (`session 75a7d7eb`, `session e0647574`, `session 9886cad3`):
1. `AutoReiv` called `write_skill_file` cold without calling `skill_view(skill_id="capability-authoring")` first, because `capability-authoring` was pinned rather than in `ON_DEMAND_SHIPPED_SKILLS`, and `mcp-engineering` was missing from `platform/agents/autoreiv.md`.
2. When writing `tools/delete_note.py`, `_static_native` failed with `"code must define a module-level def run(**kwargs)"`, baiting the model into writing an untyped `def run(**kwargs) -> dict:` signature with zero JSON Schema properties (`properties: {}`).
3. Because `delete_note.py` touched files (`access: ["files"]`), `ToolCheckService.check_native` returned `STATUS_NOT_RUN_REVIEW` without checking module imports, allowing hallucinated imports (`from functions import wiki_note_update`, `from mcp_GameDock_list_catalog import __call__`) to save unchecked.
4. When `write_skill_file` saved a non-`read_only` tool as `disabled`, no inline approval card was created in Chat; the operator had to leave Chat, open `#view-capabilities`, toggle the tool Enabled, and return to Chat.

## Cause
1. `src/application/agent_skills/allowed_tools.py` omitted `capability-authoring` and `mcp-engineering` from `ON_DEMAND_SHIPPED_SKILLS`, and `platform/agents/autoreiv.md` omitted `mcp-engineering` from `skills:`.
2. `_static_native` in `src/application/tools/tool_check.py` returned `"code must define a module-level def run(**kwargs)"`, did not reject untyped `def run(**kwargs)`-only signatures, and did not validate `import` / `from X import Y` targets via `importlib.util.find_spec` before returning `STATUS_NOT_RUN_REVIEW`.
3. `platform/skills/capability-authoring/references/authoring-guide.md` did not document the sandbox subprocess environment contract (`AUTOREIV_WIKI_PATH`, `AUTOREIV_DATA_DIR`, `AUTOREIV_PROJECTS_DIR`, ephemeral `/tmp` working directory, and no Python imports of platform/MCP tools).
4. `save_skill_file` in `src/application/skills/agora_authoring.py` saved non-`read_only` tools disabled without creating a `pending_approvals` row (`enable_skill_tool`) for inline one-click approval in Chat (`src/web/routers/hitl.py`).

## Change
- `platform/agents/autoreiv.md`, `src/application/agent_skills/allowed_tools.py`, `src/infrastructure/content/store.py`: add `mcp-engineering` to `AutoReiv` skills and reconciliation, and add `capability-authoring` and `mcp-engineering` to `ON_DEMAND_SHIPPED_SKILLS` so their tools mount on demand via `skill_view`.
- `src/application/tools/tool_check.py`: update `_static_native` to require explicit typed parameter annotations on `def run(...)` (rejecting bare `def run(**kwargs)` with no typed parameters and any unannotated parameters) and validate imported top-level module roots with `importlib.util.find_spec` so hallucinated modules (`functions`, `mcp_*`, etc.) fail the static check immediately even when `access` is non-empty.
- `platform/skills/capability-authoring/SKILL.md`, `platform/skills/capability-authoring/references/authoring-guide.md`: document the sandbox execution environment (`AUTOREIV_WIKI_PATH`, `AUTOREIV_DATA_DIR`, `AUTOREIV_PROJECTS_DIR`, isolated `/tmp` CWD, no `from functions import ...` or `/slash-command` inventions).
- `src/application/skills/agora_authoring.py`, `src/web/routers/hitl.py`, `src/web/routers/capabilities.py`, `src/application/agent_skills/tool_attachment.py`: when `save_skill_file` saves a disabled colocated tool from an agent turn, create a `pending_approvals` entry (`tool_name="enable_skill_tool"`) and return `approval_id`; resolving that approval in Chat (`POST /api/approvals/{approval_id}/decision`) calls `enable_skill_tool` and activates the skill for the session, and toggling the tool in Capabilities Studio resolves any matching pending approval.

## What dies
- Nothing (hardens existing `_static_native`, `save_skill_file`, and `ON_DEMAND_SHIPPED_SKILLS` single levers).

## Proof
- Journey `card-743-harden-agora-skill-authoring-and-inline`:
  1. Verifies `capability-authoring` and `mcp-engineering` are listed as on-demand skills on `AutoReiv` and mount their tools on `skill_view`.
  2. Verifies `write_skill_file` rejects untyped `def run(**kwargs)` and hallucinated `from functions import ...` imports with a clear static-check error.
  3. Authors a file-access colocated tool in Chat, verifies an inline `enable_skill_tool` approval card appears in Chat, approves it inline without leaving Chat, and verifies the tool is enabled, mounted, and callable immediately on the next turn.
- Checks: `tests/integration/test_card689_agora_self_build_contract.py`, `tests/unit/architecture/test_card689_agora_self_build_and_auto_enable.py`, `tests/unit/tools/test_tool_check.py`.

## Plan and decisions
- Approved by Jacob (`Option A`): Move `capability-authoring` and `mcp-engineering` to `ON_DEMAND_SHIPPED_SKILLS`, enforce typed `def run(...)` signatures and real module imports in `_static_native`, document the sandbox env contract in `authoring-guide.md`, and emit an inline `enable_skill_tool` HITL approval card in Chat when `write_skill_file` saves a non-`read_only` tool.

## Findings
- Fixed (in-area): When an agent wrote `SKILL.md` with `tools: [<colocated_tool>]` before writing `tools/<colocated_tool>.py` in the same skill folder, `make_skill_write_guard` created a duplicate `attach_tool_to_skill` approval card alongside `enable_skill_tool`. Updated `resolve_pending_skill_tool_approvals` and `make_skill_write_guard` so colocated tools in `skills/<skill_id>/tools/<name>.py` are governed solely by `enable_skill_tool` / `.tool_approvals.json`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-743-harden-agora-skill-authoring-and-inline` | desktop | PASS | Static check rejected untyped `**kwargs` and `from functions import ...`; inline `enable_skill_tool` card rendered, approved in Chat, and `check_wiki_root` executed (`/tmp/autoreiv-qa/card-743/card-743-harden-agora-skill-authoring-and-inline-desktop-02-in-chat-autoreiv-opens-capability-authoring-via-.png`, `/tmp/autoreiv-qa/card-743/card-743-harden-agora-skill-authoring-and-inline-desktop-03-approve-enable-skill-tool-inline-in-chat-and-exe.png`) |
| `card-743-harden-agora-skill-authoring-and-inline` | phone | PASS | Single inline `enable_skill_tool` card rendered and approved in Chat; `check_wiki_root` enabled, mounted, and executed (`/tmp/autoreiv-qa/card-743/card-743-harden-agora-skill-authoring-and-inline-phone-02-in-chat-autoreiv-opens-capability-authoring-via-.png`, `/tmp/autoreiv-qa/card-743/card-743-harden-agora-skill-authoring-and-inline-phone-03-approve-enable-skill-tool-inline-in-chat-and-exe.png`) |

## Release note
- **Fixed**: Hardened Agora skill and tool self-authoring by mounting `capability-authoring` and `mcp-engineering` on demand via `skill_view`, rejecting untyped `def run(**kwargs)` signatures and hallucinated module imports at static-check time, and emitting an inline Chat HITL approval card to enable non-`read_only` colocated tools (`CARD-743`).

