---
id: CARD-692
title: "Consolidate MCP servers and deep-links into Capabilities Studio and retire Skill/Tools Studio tabs"
type: feature
status: Done
priority: P1
milestone: M27
needs_decision: none
proof:
  journeys: [card-692-consolidate-mcp-servers-and-deep-links]
  checks: [tests/unit/architecture/test_card692_capabilities_consolidation.py, tests/unit/frontend/card_692_capabilities_consolidation.test.js]
branch: feat/card-691-692-agora-adoption-and-consolidation
log: {minutes: 35, qa_runs: 2, findings: 0}
created: 2026-10-16
completed: 2026-10-16
---

# CARD-692 Consolidate MCP servers and deep-links into Capabilities Studio and retire Skill/Tools Studio tabs

## Intent
Finish the UI consolidation from `ADR-0065` by folding MCP server attachment and management into the unified **Capabilities** directory tree studio (`#view-capabilities`), routing all skill/tool/MCP deep-links from Chat, Agent Studio, and Settings to `#view-capabilities`, and retiring the redundant `Skill Studio` (`#dock-skill-studio` / `#tab-skill-studio`) and `Tools Studio` (`#dock-tools-studio` / `#tab-tools-studio`) launchers from the desktop dock and navigation sidebar.

## Goal
- `#view-capabilities` includes a top-level **`mcp/` (MCP Servers)** node in the Agora tree (`#capabilitiesTreeList`) that opens the MCP Servers inspector panel (`#capabilitiesMcpPane`) where operators can view, add, test, toggle, mount, and delete platform or per-agent MCP servers.
- Deep-links from Agent Studio (`#studioOpenSkillStudioBtn`, `#forgeOpenToolsStudioBtn`, capability gap `Open in Capabilities`), Settings (`#settingsOpenToolsStudioBtn`), and Chat (`open-skill-studio`) open `#view-capabilities` (`tab: 'capabilities'`) and select the target skill folder, gap draft, or `mcp/` node.
- The desktop dock (`DOCK_LAUNCHERS`) and sidebar (`#sidebarNav`) expose **Capabilities** (`#dock-capabilities` / `#tab-capabilities`) as the single capability launcher; `dock-skill-studio`, `dock-tools-studio`, `tab-skill-studio`, and `tab-tools-studio` are removed.

## Change
- `src/web/static/modules/studios/capabilities_tree_model.js`:
  - Add the virtual `mcp/` tree node (`id: '__mcp__'`, label `mcp/ (MCP Servers)`) to `renderCapabilitiesTreeHtml` and support `mcpScope` / `mcpAgentId` in `planCapabilitiesStudioDeepLink`.
- `src/web/static/modules/studios/capabilities_studio.js`, `src/web/static/modules/services/api.js` & `src/web/templates/index.html`:
  - Add `#capabilitiesMcpPane` inside `#capabilitiesInspectorPane` (using `api.capabilities` for MCP server listing/saving/deleting and `tools_studio_catalog.js` helpers) and support gap-prefilled new skill creation when deep-linked with `{ gap }`.
- `src/web/static/app.js`:
  - Route `openSkillStudio` and `openToolsStudio` callbacks into `openCapabilitiesStudio` (`switchTab('capabilities')`).
- `src/web/static/modules/ui/agent-desktop.js` & `src/web/templates/index.html`:
  - Remove `dock-skill-studio` and `dock-tools-studio` from `DOCK_LAUNCHERS` and remove `#tab-skill-studio` and `#tab-tools-studio` from `#sidebarNav`.

## What dies
- `dock-skill-studio` and `dock-tools-studio` entries in `DOCK_LAUNCHERS` (`src/web/static/modules/ui/agent-desktop.js`).
- `#tab-skill-studio` and `#tab-tools-studio` buttons in `#sidebarNav` (`src/web/templates/index.html`).
- Legacy tab switches in `app.js` that routed `openSkillStudio` / `openToolsStudio` away from `#view-capabilities`.

## Proof
- Journey `card-692-consolidate-mcp-servers-and-deep-links`:
  1. Verify `#dock-capabilities` is present in the desktop dock and `#dock-skill-studio` / `#dock-tools-studio` / `#tab-skill-studio` / `#tab-tools-studio` are absent.
  2. Open **Settings** (`#dock-settings`), expand `Connections`, click `#settingsOpenToolsStudioBtn`, and verify it opens `#view-capabilities` directly on the `mcp/` (MCP Servers) inspector (`#capabilitiesMcpPane`).
  3. Open **Agents** (`#dock-agents`), select `Architect`, click `#studioOpenSkillStudioBtn` (`Manage skills`), and verify it opens `#view-capabilities` on the Agora skills tree with zero horizontal overflow (`scrollWidth <= innerWidth`) on both desktop (`1280x800`) and phone (`390x844`).
- Checks:
  - `tests/unit/architecture/test_card692_capabilities_consolidation.py` (`pytest.mark.guard`)
  - `tests/unit/frontend/card_692_capabilities_consolidation.test.js` (Vitest)

## Plan and decisions
- **Decision D1 (Design & Architecture — Approved)**: Fold MCP server management into `#view-capabilities` under a top-level `mcp/` tree node, route all `openSkillStudio` / `openToolsStudio` deep-links to `#view-capabilities`, and retire `dock-skill-studio` / `dock-tools-studio` from the dock and sidebar.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-692-consolidate-mcp-servers-and-deep-links` | `desktop` | PASS | Retired legacy dock/sidebar launchers; Settings MCP deep-link opened `mcp/` inspector; Agents Studio deep-link opened `#view-capabilities` (`1280px <= 1280px`) |
| `card-692-consolidate-mcp-servers-and-deep-links` | `phone` | PASS | Retired legacy dock/sidebar launchers; Settings MCP deep-link opened `mcp/` inspector; Agents Studio deep-link opened `#view-capabilities` (`390px <= 390px`) |

Screenshots:
- `/tmp/autoreiv-qa/card-692/card-692-consolidate-mcp-servers-and-deep-links-desktop-02-click-manage-in-settings-mcp-card-and-verify-it-.png`
- `/tmp/autoreiv-qa/card-692/card-692-consolidate-mcp-servers-and-deep-links-desktop-03-click-manage-skills-in-agents-studio-and-verify-.png`
- `/tmp/autoreiv-qa/card-692/card-692-consolidate-mcp-servers-and-deep-links-phone-02-click-manage-in-settings-mcp-card-and-verify-it-.png`

## Release note
- Consolidated MCP server management and all skill/tool deep-links into the unified Capabilities studio (`#view-capabilities`) and retired the separate Skill Studio and Tools Studio dock/sidebar tabs [CARD-692].
