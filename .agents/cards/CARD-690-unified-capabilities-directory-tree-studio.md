---
id: CARD-690
title: "Unified Capabilities directory tree studio"
type: feature
status: Done
priority: P1
milestone: M26
needs_decision: none
proof:
  journeys: [card-690-unified-capabilities-directory-tree-studio]
  checks: [tests/unit/architecture/test_card690_capabilities_tree_studio.py, tests/unit/frontend/card_690_capabilities_tree_studio.test.js]
branch: feat/card-690-unified-capabilities-directory-tree-studio
log: {minutes: 25, qa_runs: 2, findings: 0}
created: 2026-10-15
completed: 2026-10-15
---

# CARD-690 Unified Capabilities directory tree studio

## Intent
Deliver Slice 4 of `ADR-0065` (Milestone `M26`): provide a unified **Capabilities** directory tree studio (`dock-capabilities` / `tab-capabilities` / `view-capabilities`) where the operator can browse the Agora `skills/<id>/` folder hierarchy (`SKILL.md`, `references/*.md`, `tools/*.py`), view and edit files in place, create new skill folders or reference/tool files, inspect inferred tool schemas and `ToolCheckService` outside-access reports, and toggle colocated tools on or off with one click.

## Goal
- Opening **Capabilities** from the desktop dock (`#dock-capabilities`) or navigation sidebar (`#tab-capabilities`) displays the Agora directory tree (`#capabilitiesTreePane`) on the left and the file/tool inspector (`#capabilitiesInspectorPane`) on the right.
- Expanding a skill folder in the Agora tree shows `SKILL.md`, `references/` (`*.md`), and `tools/` (`*.py` colocated tools with risk/enable badges plus bound platform/MCP tools).
- Selecting `SKILL.md`, `references/<name>.md`, or `tools/<name>.py` loads its content into the inspector editor (`#capabilitiesFileEditor`) via `GET /api/capabilities/skills/{skill_id}/file`, and clicking **Save File** (`#capabilitiesSaveFileBtn`) saves via `PUT /api/capabilities/skills/{skill_id}/file` (running `ToolCheckService` on `tools/*.py`, auto-enabling pure `read_only` tools or saving outside-access tools as disabled).
- Selecting a colocated tool `tools/<name>.py` displays the tool status card (`#capabilitiesToolStatusCard`) with inferred description, JSON Schema parameters, risk tier, `ToolCheckService` access report, and a one-click **Enable / Disable Tool** toggle (`#capabilitiesToggleToolBtn`) calling `POST /api/capabilities/skills/{skill_id}/tools/{tool_name}/toggle`.
- Works cleanly on both desktop (`1280x800`) and phone (`390x844`) viewports with zero horizontal overflow.

## Change
- `src/web/static/modules/services/api.js`:
  - Added `api.capabilities` service methods (`tree()`, `readFile(skillId, relPath)`, `saveFile(skillId, relPath, content, sampleArguments)`, `toggleTool(skillId, toolName, enabled)`).
- `src/web/static/modules/studios/capabilities_tree_model.js`:
  - Pure formatting, normalization, filtering, and tree-node state helpers (`normalizeSkillEntry`, `filterCapabilitiesTree`, `renderCapabilitiesTreeHtml`, `renderToolStatusCardHtml`, `defaultSkillMarkdown`, `defaultReferenceMarkdown`, `defaultToolPython`) tested in Vitest.
- `src/web/static/modules/studios/capabilities_studio.js`:
  - Exported `CAPABILITIES_STUDIO_TAB = 'capabilities'`, `CAPABILITIES_STUDIO_LABEL = 'Capabilities'`, `planCapabilitiesStudioDeepLink`, and `initCapabilitiesStudio(state, callbacks)`.
- `src/web/templates/index.html`, `src/web/static/modules/ui/agent-desktop.js`, `src/web/static/app.js`:
  - Added `#tab-capabilities`, `#dock-capabilities`, `#view-capabilities`, and registered `Capabilities Studio` in `app.js` and `studioRegistry`.
- `docs/adr/0065-agora-skill-folders-and-unified-capabilities.md`:
  - Linked `CARD-690` and `test_card690_capabilities_tree_studio.py` under Slice 4 and Guard Tests.

## What dies
nothing

## Proof
- Journey `card-690-unified-capabilities-directory-tree-studio`:
  1. Author a skill folder `agora-tree-demo` with `SKILL.md`, `references/arch.md`, a pure tool `tools/format_tag.py` (auto-enabled), and a network tool `tools/ping_endpoint.py` (saved disabled).
  2. Open **Capabilities** (`#dock-capabilities`) and verify `#view-capabilities` is visible with zero horizontal overflow (`scrollWidth <= innerWidth`).
  3. Filter the Agora tree for `agora-tree-demo`, expand its folder node, and verify `SKILL.md`, `references/arch.md`, `tools/format_tag.py`, and `tools/ping_endpoint.py` appear in `#capabilitiesTreeList`.
  4. Click `references/arch.md` in the tree, verify `#capabilitiesFileEditor` loads the reference markdown, edit and click `#capabilitiesSaveFileBtn`, and verify the saved content persists.
  5. Click `tools/ping_endpoint.py` in the tree, verify `#capabilitiesToolStatusCard` shows `network` access and `Disabled (needs approval)`, click `#capabilitiesToggleToolBtn` to enable it, and verify the status updates to `Enabled` and `GET /api/capabilities/tree` confirms `enabled: true`.
- Checks:
  - `tests/unit/architecture/test_card690_capabilities_tree_studio.py` (`pytest.mark.guard`)
  - `tests/unit/frontend/card_690_capabilities_tree_studio.test.js` (Vitest)

## Plan and decisions
- **Decision D1 (Design & Architecture — `ADR-0065` Slice 4, Approved)**: Add the unified **Capabilities** Agora directory tree studio (`tab: 'capabilities'`, `#dock-capabilities`, `#view-capabilities`) backed by `/api/capabilities/tree`, `/api/capabilities/skills/{id}/file`, and `/api/capabilities/skills/{id}/tools/{tool}/toggle`, with pure tree/inspector model helpers in `capabilities_tree_model.js`.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-690-unified-capabilities-directory-tree-studio` | desktop | PASS | Agora tree rendered (`1280px <= 1280px`), `references/arch.md` edited & saved, `ping_endpoint` toggled from `Disabled (needs approval)` to `Enabled`. |
| `card-690-unified-capabilities-directory-tree-studio` | phone | PASS | Agora tree rendered (`390px <= 390px`), `references/arch.md` edited & saved, `ping_endpoint` toggled from `Disabled (needs approval)` to `Enabled`. |

Screenshots:
- `/tmp/autoreiv-qa/card-690/card-690-unified-capabilities-directory-tree-studio-desktop-02-open-capabilities-studio-and-verify-agora-tree-l.png`
- `/tmp/autoreiv-qa/card-690/card-690-unified-capabilities-directory-tree-studio-desktop-04-select-tools-ping-endpoint-py-inspect-access-rep.png`
- `/tmp/autoreiv-qa/card-690/card-690-unified-capabilities-directory-tree-studio-phone-02-open-capabilities-studio-and-verify-agora-tree-l.png`

## Release note
Added the unified Capabilities directory tree studio (`#view-capabilities`) for browsing Agora `skills/<id>/` folders (`SKILL.md`, `references/*.md`, `tools/*.py`), editing files in place, inspecting inferred schemas and safety checks, and toggling colocated tools on or off (CARD-690, ADR-0065).
