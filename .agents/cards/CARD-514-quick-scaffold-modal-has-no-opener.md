---
id: CARD-514
title: "Agent Studio's Quick Scaffold modal has no opener (dead UI)"
status: Done
completed: 2026-09-29
created: 2026-09-25
branch: qa
related:
  - CARD-496
  - CARD-197
labels:
  - type:cleanup
  - area:agents
  - area:frontend
  - P3
needs_decision: none
milestone: M21
---

# [CARD-514] Agent Studio's Quick Scaffold modal has no opener

> **Status**: Done (closed in CARD-577). Superseded by CARD-569: Agent Studio New Agent now opens the Quick Scaffold modal; CARD-577 removed only the dead #forgeQuickScaffoldBtn hook.
> **Related**: CARD-496 (removes only this modal's Factory jump, D6), CARD-197 (origin)
> **Labels**: `type:cleanup`, `area:agents`, `area:frontend`, `P3`

## Problem

- `#forgeNewAgentModal` ("Quick Scaffold Specialist Agent", `templates/index.html` L5018) and its JS (`forge/scaffold.js` L111, L240-345: presets, `openQuickScaffoldModal`, a submit that posts `/api/agents`) are only opened by `#forgeQuickScaffoldBtn` (`scaffold.js` L248, L270-274).
- That button is **not in the template**. On a scratch server, the button is absent and nothing opens the modal.
- Agent Studio's **New Agent** button hands off to AutoReiv chat instead (`forge.js` L657-664, `app.js` L276-281).

## Change

Confirm again that nothing opens the modal (rg plus a smoke check), then delete the modal markup, `FORGE_QUICK_PRESETS`, `openQuickScaffoldModal`, `closeQuickScaffoldModal` and the submit handler, and update their tests. Alternatively, if Jacob wants a form-based "new agent" in Agent Studio, add a visible button instead, which is a product decision.

## Done when

No unreachable Quick Scaffold code or markup remains (or it has a visible opener, per Jacob); New Agent still hands off to AutoReiv; tests pass.

## Log
- 2026-09-29: Closed in CARD-577. Superseded by CARD-569: Agent Studio New Agent now opens the Quick Scaffold modal; CARD-577 removed only the dead #forgeQuickScaffoldBtn hook.
