---
id: CARD-705
title: "Retire stale Developer/Toolsmith/Architect references and remove Chat header role pill"
type: bug
status: Ready
priority: P3
milestone: M30
needs_decision: none
proof:
  journeys: [card-705-retire-stale-developertoolsmitharchitect-references-and-remove]
  checks: [tests/unit/architecture/test_card705_no_retired_agent_refs.py]
branch: feat/card-705-retire-stale-developertoolsmitharchitect-references-and-remove
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-705 Retire stale Developer/Toolsmith/Architect references and remove Chat header role pill

## Problem
1. Although `Developer`, `Toolsmith`, and `Architect` were retired as separate shipped agents in `CARD-693` (their skills moved into `AutoReiv` via `capability-authoring`, `project-cards`, and `software-development`), live Chat turns still surface:
   - `"You can use Ask Developer to add this."` at the end of assistant replies (`ask_developer_ending` in `src/application/kernel/reply_rules.py`),
   - the purple **`Ask Developer`** action pill (`ask-developer-btn`) in the message action bar (`src/web/static/js/slices/chat/chat_messages.js`, `chat_modals.js`, `chat_actions.js`),
   - stale references to routing to `Developer` / `Toolsmith` / `Architect` in `domain_line`, `WITHHELD_PLATFORM_TOOLS`, `RETIRED_LIVE_AGENT_IDS`, skill runbooks, and stale user-data `agents/autoreiv.md` copies whose `based_on` hash predates `CARD-693`.
2. In the Chat window header (`#view-chat`), right next to the active agent selector, there is a static pill-shaped span (`#activeAgentRole` / `"Autonomous Multi-Agent Orchestrator"`) that is truncated (`"Autonomous Multi-A..."`), provides no interactive functionality, and wastes header space.

## Cause
- `src/application/kernel/reply_rules.py` (`ASK_DEVELOPER_LINE`, `ask_developer_ending`), `src/application/agent_skills/allowed_tools.py`, `src/domain/agents/profiles.py`, and `src/web/static/js/slices/chat/*` still contain pre-`CARD-693` `Ask Developer` / `Developer` / `Toolsmith` / `Architect` handoff strings and buttons.
- `src/web/templates/partials/chat_view.html` and `src/web/static/js/slices/chat/chat_sessions.js` render `#activeAgentRole` (`"Autonomous Multi-Agent Orchestrator"`) next to `#chatAgentSelect` with no click action or real meaning.

## Change
- Audit and remove stale `Ask Developer`, `Developer`, `Toolsmith`, and `Architect` agent references across backend prompts/rules (`reply_rules.py`, `allowed_tools.py`, `profiles.py`, `agent_kernel.py`, `platform/skills/*`), frontend Chat action buttons/modals (`chat_messages.js`, `chat_modals.js`, `chat_actions.js`), and reconcile stale pre-`CARD-693` user agent prompt copies where appropriate.
- Verify `#activeAgentRole` (`"Autonomous Multi-Agent Orchestrator"`) in `#view-chat` provides no functionality and remove it from `src/web/templates/partials/chat_view.html` and its JS writers.

## What dies
- `ASK_DEVELOPER_LINE` / `"You can use Ask Developer to add this."` in `src/application/kernel/reply_rules.py`.
- `.ask-developer-btn` button and `Ask Developer` modal/action wiring in `src/web/static/js/slices/chat/`.
- `#activeAgentRole` (`"Autonomous Multi-Agent Orchestrator"`) static pill next to the agent selector in `src/web/templates/partials/chat_view.html`.

## Proof
- Journey `card-705-retire-stale-developertoolsmitharchitect-references-and-remove`:
  1. Open Chat (`#view-chat`), verify the `"Autonomous Multi-Agent Orchestrator"` static pill next to the agent name is gone, send a turn to `AutoReiv` asking what capabilities/tools it has and what it cannot directly do, and verify the reply and message action bar contain no `Ask Developer` text, no `Ask Developer` button, and no routing instructions to retired `Developer`/`Toolsmith`/`Architect` agents on desktop and phone.
- Checks:
  - `tests/unit/architecture/test_card705_no_retired_agent_refs.py`

## Plan and decisions
- Scoped per Jacob's instructions and screenshots (2026-10-17).

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
- Removed stale `Ask Developer` / `Developer` / `Toolsmith` / `Architect` agent references and buttons, and removed the non-functional `"Autonomous Multi-Agent Orchestrator"` pill from the Chat header [CARD-705].
