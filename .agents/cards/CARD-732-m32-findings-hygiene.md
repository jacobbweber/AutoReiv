---
id: CARD-732
title: "M32 findings hygiene: retire developer prompt check, fix journey tab navigation, and share askAndApprove"
type: bug
status: Done
completed: 2026-10-19
priority: P2
milestone: M32
needs_decision: none
proof:
  journeys: [card-709-web-and-ui-wiring-fixes, card-707-lifecycle-data-safety]
  checks: [tests/unit/architecture/test_card693_agent_skill_consolidation.py, tests/unit/agents/test_developer_project_grounding.py]
branch: feat/card-732-m32-findings-hygiene
log: {minutes: 22, qa_runs: 1, findings: 1}
created: 2026-10-19
---

# CARD-732 M32 findings hygiene: retire developer prompt check, fix journey tab navigation, and share askAndApprove

## Problem
Four M32 post-release hygiene items were logged in `docs/findings.md` during `CARD-728`–`CARD-730`:
1. `tests/e2e/journeys/card-709-web-and-ui-wiring-fixes.mjs` step 3 (Settings model discovery) and `card-707-lifecycle-data-safety.mjs` call `window.__autoreivSwitchTab`, which was retired in `CARD-716`, causing `card-709` step 3 to time out waiting for `#view-settings`.
2. `src/application/kernel/system_prompt_builder.py` still checks `getattr(agent, "id", None) == "developer"` for the retired `developer` agent (`ADR-0066`), violating the `ADR-0061` boundary rule against `agent.id` special cases.
3. `AGENTS.md` under "Product locks" still states that "the model sees at most 15 per turn", which was removed by `ADR-0064` and `ADR-0065`.
4. `tests/e2e/journeys/card-562-developer-one-card-to-in-review.mjs` and `card-563-architect-plans-and-hands-off.mjs` keep local `askAndApprove` functions instead of using `tests/e2e/journeys/lib/app.mjs`, and 7 journey files duplicate `openTab(page, tabName)`.

## Cause
- `CARD-716` removed `window.__autoreivSwitchTab` from `src/web/static/`, but `card-709`, `card-707`, `card-704`, `card-703`, and `card-701` still referenced it in `page.evaluate(...)`.
- `system_prompt_builder.py` line 100 retained `is_developer = getattr(agent, "id", None) == "developer"` from pre-`ADR-0066` code.
- `AGENTS.md` line 48 was not updated when `ADR-0064` retired `MAX_ACTIVE_TOOLS_PER_TURN`.
- `askAndApprove` in `lib/app.mjs` lacked the optional `{ idleLimit, progress, onApprove }` parameters used by `card-563`, and `openTab` had not been extracted to `lib/app.mjs`.

## Change
- `src/application/kernel/system_prompt_builder.py`: remove `is_developer` so active project context is injected solely when `has_project_tools` is true.
- `AGENTS.md`: update the product lock bullet to reflect `ADR-0064` and `ADR-0065` (no per-turn 15-tool cap; tools from pinned skills and `skill_view`-mounted skills are sent).
- `tests/e2e/journeys/lib/app.mjs`: add shared `openTab(page, tabName)` and extend `askAndApprove` with optional `{ idleLimit = 8, progress = null, onApprove = null }`.
- `tests/e2e/journeys/card-709-web-and-ui-wiring-fixes.mjs`, `card-707-lifecycle-data-safety.mjs`, `card-704-staged-rca-self-healing-proposals.mjs`, `card-703-local-inference-port-auto-probing.mjs`, `card-701-live-approval-mode-and-effect-tiers.mjs`, `card-692`, `card-693`, `card-694`, `card-717`, `card-718`, `card-719`, `card-720`, `card-562`, `card-563`: use shared `openTab` and `askAndApprove` from `lib/app.mjs`.
- `docs/findings.md`: remove the triaged M32 findings.

## What dies
- `is_developer` in `src/application/kernel/system_prompt_builder.py`.
- All `window.__autoreivSwitchTab(...)` calls across `tests/e2e/journeys/*.mjs`.
- Duplicate `askAndApprove` functions in `card-562` and `card-563` and duplicate `openTab` functions in `card-692`, `card-693`, `card-694`, `card-717`, `card-718`, `card-719`, and `card-720`.

## Proof
- Journey `card-709-web-and-ui-wiring-fixes`: all 3 steps pass on desktop and phone, including step 3 opening `#view-settings` and verifying `X-Provider-Api-Key`.
- Journey `card-707-lifecycle-data-safety`: both steps pass on desktop and phone, opening `#view-capabilities` and `#view-settings` via `openTab`.
- Checks: guard tests in `tests/unit/architecture/test_card693_agent_skill_consolidation.py` and unit tests in `tests/unit/agents/test_developer_project_grounding.py` (including negative assertion that an agent with `id="developer"` and no project tools does not receive active project context).

## Plan and decisions
- Technical only (`needs_decision: none`): centralize `openTab` and `askAndApprove` in `tests/e2e/journeys/lib/app.mjs` so every journey uses one helper.

## Findings
- (fixed) `card-701`, `card-703`, `card-704`, and `card-707` also had `window.__autoreivSwitchTab` calls, and 7 journeys had duplicate `openTab` definitions; all consolidated onto `openTab` in `lib/app.mjs`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-707-lifecycle-data-safety | desktop | PASS | 2/2 steps: Capabilities Studio customization + Settings Studio Vault credential |
| card-707-lifecycle-data-safety | phone | PASS | 2/2 steps |
| card-709-web-and-ui-wiring-fixes | desktop | PASS | 3/3 steps: Study entry, active project pill, and Settings Studio X-Provider-Api-Key header |
| card-709-web-and-ui-wiring-fixes | phone | PASS | 3/3 steps |
| preflight --fast --base qa | - | GREEN | ruff PASS, eslint PASS (0 warnings), guard 315, changed 11, vitest 1139 |

Screenshots:
- `/tmp/autoreiv-qa/card-732/card-709-web-and-ui-wiring-fixes-desktop-03-verify-settings-studio-model-discovery-sends-api.png`
- `/tmp/autoreiv-qa/card-732/card-709-web-and-ui-wiring-fixes-phone-03-verify-settings-studio-model-discovery-sends-api.png`
- `/tmp/autoreiv-qa/card-732/card-707-lifecycle-data-safety-desktop-02-save-encrypted-credential-in-credential-vault-an.png`

## Release note
Fixed: Retired the leftover `agent.id == "developer"` prompt check in `system_prompt_builder.py`, replaced removed `window.__autoreivSwitchTab` calls in live journeys with shared `openTab` in `lib/app.mjs`, and unified `askAndApprove` across journeys (CARD-732).
