---
id: CARD-742
title: "Prune dead view-skill-studio and view-tools-studio DOM and JS remnants"
type: bug
status: Done
priority: P2
milestone: M33
needs_decision: none
proof:
  journeys: [card-742-prune-dead-view-skill-studio-and]
  checks:
    - tests/unit/architecture/test_card692_capabilities_consolidation.py
    - tests/unit/frontend/dom_audit.test.js
    - tests/unit/frontend/card_692_capabilities_consolidation.test.js
branch: feat/card-742-prune-dead-view-skill-studio-and
log: {minutes: 25, qa_runs: 1, findings: 0}
created: 2026-10-24
completed: 2026-10-24
---

# CARD-742 Prune dead view-skill-studio and view-tools-studio DOM and JS remnants

## Problem
After `CARD-690` and `CARD-692` consolidated Skill Studio and Tools Studio into the unified Capabilities Studio (`#view-capabilities`, `src/web/static/modules/studios/capabilities_studio.js`), the superseded `<section id="view-skill-studio">` (`src/web/templates/partials/prompts_education_skill_studio.html`) and `<section id="view-tools-studio">` (`src/web/templates/partials/tools_capabilities.html`) DOM trees (~385 lines of dead HTML) and their unmounted JS controllers (`src/web/static/modules/studios/skill_studio.js` and `src/web/static/modules/studios/tools_studio.js`) remained in the tree, violating the single-lever / zero-dead-DOM rule.

## Cause
`CARD-692` retired `#dock-skill-studio` and `#dock-tools-studio` and removed `initSkillStudio` / `initToolsStudio` from `src/web/static/app.js`, but kept `#view-skill-studio`, `#view-tools-studio`, `skill_studio.js`, `tools_studio.js`, and `'skill-studio'` / `'tools-studio'` in `VIEW_BY_TAB` because older unit tests still sliced those DOM views and read those files directly.

## Change
1. Delete `<section id="view-skill-studio">` from `src/web/templates/partials/prompts_education_skill_studio.html` and `<section id="view-tools-studio">` from `src/web/templates/partials/tools_capabilities.html`.
2. Delete the unmounted controllers `src/web/static/modules/studios/skill_studio.js` and `src/web/static/modules/studios/tools_studio.js`.
3. Remove `'skill-studio'` and `'tools-studio'` from `VIEW_BY_TAB` in `src/web/static/modules/ui/agent-desktop.js`, map `'skill-studio'` / `'tools-studio'` to `'capabilities'` in `resolveDesktopStudioTab`, add `'skill-studio'` and `'tools-studio'` to `RETIRED_DESKTOP_TABS` in `src/web/static/modules/ui/agent_desktop/prefs.js`, and move `'autoreiv_tools_studio_agent_id'` (`#toolsStudioAgentSelect`) into `RETIRED_PICKER_STORAGE_KEYS` in `src/web/static/modules/studios/agent_picker.js`.
4. Update the guard and unit tests to assert that `#view-skill-studio`, `#view-tools-studio`, `skill_studio.js`, and `tools_studio.js` are gone and `#view-capabilities` / `capabilities_studio.js` is the single Capabilities surface.

## What dies
- `<section id="view-skill-studio">` and its `#skillStudio`, `#factorySaveSkillBtn`, `#factoryExistingSkillSelect`, `#factorySkillMarkdownEditor`, `#factoryCapabilitiesContainer`, `#skillStudioFileStatus`, `#skillStudioDeleteBtn` DOM elements in `src/web/templates/partials/prompts_education_skill_studio.html`.
- `<section id="view-tools-studio">` and its `#toolsStudio`, `#toolsStudioIntentForm`, `#toolsStudioCatalog`, `#toolsStudioMcpList`, `#toolsStudioMcpSaveBtn`, `#toolsStudioScopeSelect`, `#toolsStudioAgentSelect` DOM elements in `src/web/templates/partials/tools_capabilities.html`.
- `src/web/static/modules/studios/skill_studio.js` (`initSkillStudio`, `planSkillStudioDeepLink`, `SKILL_STUDIO_TAB`, `SKILL_STUDIO_LABEL`).
- `src/web/static/modules/studios/tools_studio.js` (`initToolsStudio`).
- `'skill-studio': 'view-skill-studio'` and `'tools-studio': 'view-tools-studio'` in `VIEW_BY_TAB` (`src/web/static/modules/ui/agent-desktop.js`).
- `PICKER_KEYS.tools` / `#toolsStudioAgentSelect` binding in `src/web/static/modules/studios/agent_picker.js` (retired into `RETIRED_PICKER_STORAGE_KEYS`).

## Proof
- Journey `card-742-prune-dead-view-skill-studio-and`:
  1. Open the app, verify `#view-skill-studio` and `#view-tools-studio` do not exist in the DOM (`count === 0`), and verify `#view-capabilities` is the single Capabilities view.
  2. Open Capabilities Studio (`#dock-capabilities`), verify the Agora skill tree (`SKILL.md`, `references/`, `tools/`) and `+ New Skill` creation bar work cleanly with zero horizontal overflow on desktop and phone.
  3. Select `mcp/ (MCP Servers)` in the Capabilities tree and verify `#capabilitiesMcpPane` renders the MCP scope, agent selector (`#capabilitiesMcpAgentSelect`), and server list cleanly.
- Checks:
  - `tests/unit/architecture/test_card692_capabilities_consolidation.py` (guard asserting `#view-skill-studio`, `#view-tools-studio`, `skill_studio.js`, and `tools_studio.js` are absent)
  - `tests/unit/frontend/dom_audit.test.js`
  - `tests/unit/frontend/card_692_capabilities_consolidation.test.js`

## Plan and decisions
- Approved by Jacob ("Can we do option c from earlier now?"): prune the dead `#view-skill-studio` and `#view-tools-studio` DOM sections and their unused `skill_studio.js` and `tools_studio.js` modules while keeping shared pure helpers (`tools_studio_catalog.js`, `tools_studio_authoring.js`, `skill_studio/*`) that are actively imported by `capabilities_studio.js`, `forge/tools.js`, `settings.js`, `observability.js`, and `chat/teach_modal.js`.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-742-prune-dead-view-skill-studio-and` | desktop | PASS | 0 legacy Skill/Tools Studio DOM nodes, `#view-capabilities` Agora skill tree, `+ New Skill` bar, and `#capabilitiesMcpPane` verified at `1280px <= 1280px`. |
| `card-742-prune-dead-view-skill-studio-and` | phone | PASS | 0 legacy Skill/Tools Studio DOM nodes, `#view-capabilities` Agora skill tree, `+ New Skill` bar, and `#capabilitiesMcpPane` verified at `390px <= 390px`. |

Screenshots:
- `/tmp/autoreiv-qa/card-742/card-742-prune-dead-view-skill-studio-and-desktop-02-2-open-capabilities-studio-and-verify-agora-skil.png`
- `/tmp/autoreiv-qa/card-742/card-742-prune-dead-view-skill-studio-and-desktop-03-3-select-mcp-mcp-servers-in-capabilities-studio-.png`
- `/tmp/autoreiv-qa/card-742/card-742-prune-dead-view-skill-studio-and-phone-02-2-open-capabilities-studio-and-verify-agora-skil.png`

## Release note
- **Fixed (CARD-742):** Pruned the superseded `#view-skill-studio` and `#view-tools-studio` DOM trees and unmounted `skill_studio.js` / `tools_studio.js` controllers so `#view-capabilities` (`capabilities_studio.js`) is the single Capabilities Studio surface.
