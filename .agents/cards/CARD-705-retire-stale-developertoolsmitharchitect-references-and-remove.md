---
id: CARD-705
title: "Retire stale Developer/Toolsmith/Architect references and remove Chat header role pill"
type: bug
status: Done
priority: P3
milestone: M30
needs_decision: none
proof:
  journeys: [card-705-retire-stale-developertoolsmitharchitect-references-and-remove]
  checks: [tests/unit/architecture/test_card705_no_retired_agent_refs.py]
branch: feat/card-705-retire-stale-developertoolsmitharchitect-references-and-remove
log: {minutes: 20, qa_runs: 2, findings: 0}
created: 2026-10-17
completed: 2026-10-17
---

# CARD-705 Retire stale Developer/Toolsmith/Architect references and remove Chat header role pill

## Problem
1. Although `Developer`, `Toolsmith`, and `Architect` were retired as separate shipped agents in `CARD-693` (their skills moved into `AutoReiv` via `capability-authoring`, `project-cards`, and `software-development`), live Chat turns still surfaced:
   - `"You can use Ask Developer to add this."` at the end of `AutoReiv` replies (`ask_developer_ending` in `src/application/kernel/reply_rules.py`),
   - the purple **`Ask Developer`** action pill (`.msg-ask-developer-btn`) in the message action bar (`src/web/static/modules/studios/chat/render.js`),
   - stale instructions to direct the operator to `Developer in Chat` in `platform/skills/platform-health/SKILL.md`, and stale user-data `agents/autoreiv.md` copies (such as `Ava` on Jarvis) whose `based_on` hash predated `CARD-693` and still carried only 12 skills plus an old system prompt telling her to `"route to Developer/Toolsmith agents"`.
2. In the Chat window header (`#view-chat`), right next to the active agent selector (`#agentSelect`), there was a static pill-shaped span (`#activeAgentTone`: `"Autonomous Multi-Agent Orchestrator"` / `"Engine: AutoReiv"`) that was truncated (`"Autonomous Multi-A..."`), had zero event listeners, and wasted header space.

## Cause
- `is_toolsmith(agent)` in `src/application/kernel/reply_rules.py` only checked `agent.id == "toolsmith"`. After `CARD-693` consolidated `Toolsmith` into `AutoReiv` (`capability-authoring`), `is_toolsmith(autoreiv)` returned `False`, so `agent_kernel.py` passed `offer=True` to `ask_developer_ending`, appending `"You can use Ask Developer to add this."` and triggering `offersAskDeveloper` in `render.js` to render `.msg-ask-developer-btn`.
- `ContentStore` (`src/infrastructure/content/store.py`) loaded stale pre-`CARD-693` user copies of `autoreiv.md` (`based_on != shipped_hash`) without reconciling the consolidated `CARD-693` skills (`capability-authoring`, `project-cards`, `software-development`, `user:*`) or upgrading stale prompts mentioning `Developer/Toolsmith`.
- `platform/skills/platform-health/SKILL.md` still instructed directing the operator to `Developer in Chat`.
- `src/web/templates/index.html` and `src/web/static/modules/studios/chat.js` rendered and updated `#activeAgentTone` (`"Autonomous Multi-Agent Orchestrator"`) with no interactive behavior.

## Change
- Removed `#activeAgentTone` from `src/web/templates/index.html` and `src/web/static/modules/studios/chat.js`.
- Updated `is_toolsmith(agent)` and `_ASK_DEVELOPER_TEXT` in `src/application/kernel/reply_rules.py` so any agent carrying `capability-authoring` (including `AutoReiv`) is recognized as the capability-authoring agent (`offer=False` in `ask_developer_ending`), stripping any `Ask Developer` sentence and never appending `ASK_DEVELOPER_LINE` or rendering `.msg-ask-developer-btn` on `AutoReiv` replies.
- Updated `_Kind` in `src/infrastructure/content/store.py` to automatically reconcile stale pre-`CARD-693` user copies of `autoreiv.md` (`based_on != shipped_hash`) with the consolidated `CARD-693` skills and clean shipped prompt while preserving user metadata (`name: Ava`, `tone`, `avatar`, etc.), and to ignore leftover user copies of retired shipped agents (`developer`, `toolsmith`, `architect`) that have `based_on` set.
- Updated `BuiltinAgentRegistry.get_agent` in `src/infrastructure/agents/registry.py` to fall back to `autoreiv` when a retired shipped agent id (`developer`, `toolsmith`, `architect`) is requested and no custom profile is registered.
- Updated `platform/skills/platform-health/SKILL.md` to remove `"direct the operator to Developer in Chat"`.

## What dies
- `#activeAgentTone` (`"Autonomous Multi-Agent Orchestrator"` / `"Engine: AutoReiv"`) in `src/web/templates/index.html` and `src/web/static/modules/studios/chat.js`.
- Stale `"direct the operator to Developer in Chat"` instruction in `platform/skills/platform-health/SKILL.md`.
- Leftover user copies of retired shipped agents (`developer.md`, `toolsmith.md`, `architect.md` with `based_on`) in `ContentStore`.

## Proof
- Journey `card-705-retire-stale-developertoolsmitharchitect-references-and-remove`:
  1. Open Chat (`#view-chat`), verify `#activeAgentTone` (`"Autonomous Multi-Agent Orchestrator"` / `"Engine: AutoReiv"`) is absent from the DOM, and verify `GET /api/agents/autoreiv` has `capability-authoring`, `project-cards`, `software-development`, and `user:*` with no stale `Developer/Toolsmith` prompt text.
  2. Send a Chat turn on `AutoReiv` running `inspect_system_health` and noting raw shell commands are not used during health checks, and verify the reply and message action bar contain no `Ask Developer` text, zero `.msg-ask-developer-btn` buttons, and no `"Developer in Chat"` references on desktop and phone.
- Checks:
  - `tests/unit/architecture/test_card705_no_retired_agent_refs.py`

## Plan and decisions
- Scoped per Jacob's instructions and screenshots (2026-10-17).

## Findings
- None.

## Results
| Journey / Check | Viewport | Result | Notes |
|---|---|---|---|
| `preflight.py --fast --base qa` | — | PASS (GREEN) | ruff PASS, eslint PASS, pytest guard 255 passed, changed tests 4 passed, mapped tests 476 passed, vitest 1124 passed |
| `card-705-retire-stale-developertoolsmitharchitect-references-and-remove` | desktop | PASS | Chat header has no `#activeAgentTone` pill; `AutoReiv` health check reply has zero `.msg-ask-developer-btn` buttons or stale `Developer` text |
| `card-705-retire-stale-developertoolsmitharchitect-references-and-remove` | phone | PASS | Same verified on mobile viewport |

Screenshots (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-705\`):
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-705\card-705-retire-stale-developertoolsmitharchitect-references-and-remove-desktop-01-verify-chat-header-has-no-activeagenttone-static.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-705\card-705-retire-stale-developertoolsmitharchitect-references-and-remove-desktop-02-verify-autoreiv-health-check-reply-never-appends.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-705\card-705-retire-stale-developertoolsmitharchitect-references-and-remove-phone-02-verify-autoreiv-health-check-reply-never-appends.png`

## Release note
- Removed stale `Ask Developer` / `Developer` / `Toolsmith` / `Architect` agent references and buttons on `AutoReiv` replies, reconciled pre-`CARD-693` user `autoreiv.md` copies (`Ava`), and removed the non-functional `"Autonomous Multi-Agent Orchestrator"` pill from the Chat header [CARD-705].
