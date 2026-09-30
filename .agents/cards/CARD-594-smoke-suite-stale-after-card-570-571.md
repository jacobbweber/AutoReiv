---
id: CARD-594
title: "Smoke suite red since CARD-570/571/574: 14 Playwright tests still expected Developer, the old escalation key, the restart warning and Developer's coding skill"
status: Done
created: 2026-09-30
completed: 2026-09-30
branch: qa
related:
  - CARD-570
  - CARD-571
  - CARD-574
labels:
  - type:bug
  - area:tests
  - P1
needs_decision: none
milestone: M25
---

# [CARD-594] Smoke suite red since CARD-570/571/574

> **Status**: Done (merged into qa 2026-09-30)
> **Observed during**: CARD-551 merge 2026-09-30 (full preflight RED on smoke; finding line 2026-09-30).

## Why
Full preflight's smoke stage had 14 failures (7 tests x desktop/phone) since the CARD-571 merge `d44814f3`, so every card merged on a red smoke run. Jacob asked to make full preflight green again.

## Root cause (each is a stale test, not a product bug)
| Test | Failure | Intentional product change |
|---|---|---|
| TC-34 | `draft.tool_name` empty | CARD-574 dropped the `factory_escalation` migration; the fixture still used the old key. Its Talk mock also answered `agent_id: developer`. |
| TC-39, TC-44, TC-45 | chat never opened / `agent_id` toolsmith | CARD-571: every Ask Developer button opens a **Toolsmith** chat; `interpretAuthoringTalk` refuses a Talk reply for another agent. The mocks still said `developer`. |
| TC-37 | restart-warning toast missing | CARD-570: adopted skills are files that survive restart; the warning was removed on purpose (unit test `adopt_status_502` already says so). |
| TC-38 | Developer `coding` pill unticked | CARD-570/562: Developer is a card worker (project-orientation ... implement-change ...), no `coding` skill. |
| TC-42 | runtime tool not in the catalog | CARD-570: a runtime-built tool is saved **disabled** and listed under "Runtime-built tools" until Jacob enables it; the catalog (with the check label) shows it once enabled. |

## Change (tests only)
- `tests/e2e/smoke.spec.js`: Talk mocks and hand-off sessions use `toolsmith`; TC-44/45 expect the stream on `toolsmith`; TC-34 fixture uses `tool_escalation`; TC-37 expects the plain "is on for autoreiv" toast and no restart warning; TC-38 expects Developer's `implement-change` pill ticked and `coding` unticked; TC-42 enables the good and high-risk tools through `POST /api/tools/native/<name>/enable` before checking the catalog rows and check labels (the broken tool is still refused with 422).

## Evidence
- Before: `npx playwright test tests/e2e/smoke.spec.js` -> 14 failed, 59 passed (6.6 min).
- After: the 14 pass (`-g "TC-34|TC-37|TC-38|TC-39|TC-42|TC-44|TC-45"`, 1.1 min); full preflight below.

## Log
- 2026-09-30: filed and fixed (Jacob: fix the 14 smoke tests so full preflight is green; merge when green).
