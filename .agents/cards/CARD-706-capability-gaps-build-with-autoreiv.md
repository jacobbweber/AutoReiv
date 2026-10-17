---
id: CARD-706
title: Replace capability gap Open in Skill Studio and Ask Developer buttons with Build with AutoReiv
status: In Review
priority: P1
milestone: M28
proof:
  journeys:
    - card-706-capability-gaps-build-with-autoreiv
  checks:
    - pytest tests/unit/architecture/test_card706_capability_gaps_build_with_autoreiv.py
    - npx vitest run tests/unit/frontend/card_496_retire_factory_ui.test.js tests/unit/frontend/card_522_gap_prefill.test.js tests/unit/frontend/chat_train_workbench_keep_one_306.test.js tests/unit/frontend/auto_train_backlog.test.js
log:
  - 2026-10-17: Created card from Jacob's approval (Build) of Option 1 for capability gap recommendations in Agents Studio.
  - 2026-10-17: Replaced Open in Skill Studio and Ask Developer buttons on capability gap rows with Build with AutoReiv, resolved authoring/gap chats onto AutoReiv, added capability-authoring guidance to format_developer_prompt, verified preflight --fast and live_qa desktop + phone PASS.
---

## Problem
Under Agents Studio (`#agentBacklogList`), capability gap rows still render two pre-M26 buttons (`Open in Skill Studio` and `Ask Developer`), and clicking `Ask Developer` opens a session bound to retired `toolsmith` rather than selecting `AutoReiv` (`autoreiv`) in Chat. With Skills Studio and Tools Studio retired in M26 (`CARD-691`) and `Developer`/`Toolsmith` consolidated into `AutoReiv` in M27 (`CARD-693`), capability gap recommendations should have a single **`Build with AutoReiv`** button alongside **`Dismiss`** that opens a Chat session with `AutoReiv` pre-prompted with the capability gap details and instructions to author the skill/tool (`skill_view(skill_id="capability-authoring")` / `register_native_tool`).

## Cause
1. `capabilityGapRowHtml` and `loadAgentCapabilityGaps` in `src/web/static/modules/studios/forge/tools.js` still rendered `.btn-gap-open-skill-studio` (`Open in Skill Studio`) and `.btn-gap-ask-developer` (`Ask Developer`).
2. `openDeveloperSession` in `src/web/static/modules/studios/chat.js` assigned `state.selectedAgentId = agentId` (`'toolsmith'`) without resolving retired agent IDs to `'autoreiv'`, and `store.list_sessions(agent_id="autoreiv")` in `src/infrastructure/memory/repositories/sessions.py` did not include sessions created via `/api/tools_studio/authoring/talk`, causing `loadSessions()` to switch away from the newly opened session.
3. `format_developer_prompt` in `src/application/tools/developer_mediation.py` did not mention `skill_view(skill_id="capability-authoring")` for authoring Agora skill folders.

## Decision
Option 1 (approved by Jacob with `Build`):
- Replace `Open in Skill Studio` and `Ask Developer` on capability gap rows with a single primary **`Build with AutoReiv`** button alongside **`Dismiss`**.
- Resolve authoring/gap sessions onto `AutoReiv` (`autoreiv`) in `openDeveloperSession` (`resolveAuthoringChatAgentId`) and include retired-agent authoring sessions in `store.list_sessions(agent_id="autoreiv")` so the new Chat session stays active under `AutoReiv` and immediately streams the pre-prompted turn.
- Include `skill_view(skill_id="capability-authoring")` in `format_developer_prompt` so `AutoReiv` can author an Agora skill folder (`SKILL.md` + `tools/<tool_name>.py`) or register a native tool.

## Change
- `src/web/static/modules/studios/forge/tools.js`: update `capabilityGapRowHtml` to render a single **`Build with AutoReiv`** button (`.btn-gap-ask-developer.btn-gap-build-autoreiv`) and **`Dismiss`** (`.btn-dismiss-gap`), removing `.btn-gap-open-skill-studio` (`Open in Skill Studio`) from gap rows. Update error toast wording in `askDeveloperAboutGap` to say `AutoReiv chat`.
- `src/web/static/modules/studios/chat/developer_intent.js` & `src/web/static/modules/studios/chat.js`: add `resolveAuthoringChatAgentId` and use it in `openDeveloperSession` to resolve retired agent IDs (`toolsmith`, `developer`, `architect`) to `autoreiv` so `#agentSelect` and `#activeAgentTitle` stay on `AutoReiv`.
- `src/infrastructure/memory/repositories/sessions.py`: in `list_sessions`, when `agent_id == "autoreiv"`, include sessions created under `('autoreiv', 'toolsmith', 'developer', 'architect')` so authoring/gap sessions remain in `AutoReiv`'s session list when `loadSessions()` runs.
- `src/application/tools/developer_mediation.py`: reference `skill_view(skill_id="capability-authoring")` in `format_developer_prompt`.

## What dies
- `.btn-gap-open-skill-studio` (`Open in Skill Studio`) and `Ask Developer` button label on capability gap rows in `src/web/static/modules/studios/forge/tools.js`.

## Proof
- Guard test: `tests/unit/architecture/test_card706_capability_gaps_build_with_autoreiv.py`.
- Frontend unit tests: `tests/unit/frontend/card_496_retire_factory_ui.test.js`, `tests/unit/frontend/card_522_gap_prefill.test.js`, `tests/unit/frontend/chat_train_workbench_keep_one_306.test.js`, `tests/unit/frontend/auto_train_backlog.test.js`.
- Live journey: `tests/e2e/journeys/card-706-capability-gaps-build-with-autoreiv.mjs` on desktop and phone.

| Check / Journey | Result | Note |
|---|---|---|
| `preflight.py --fast --base qa` | PASS | ruff, eslint, 258 guard tests, 3 changed tests, 91 mapped tests, 1,124 vitest tests (14 s) |
| `card-706-capability-gaps-build-with-autoreiv` (desktop) | PASS | Step 1 + Step 2 pass |
| `card-706-capability-gaps-build-with-autoreiv` (phone) | PASS | Step 1 + Step 2 pass |

Screenshots:
- `/tmp/autoreiv-qa/card-706/card-706-capability-gaps-build-with-autoreiv-desktop-01-agents-studio-capability-gap-row-renders-build-w.png`
- `/tmp/autoreiv-qa/card-706/card-706-capability-gaps-build-with-autoreiv-desktop-02-clicking-build-with-autoreiv-opens-chat-on-autor.png`
- `/tmp/autoreiv-qa/card-706/card-706-capability-gaps-build-with-autoreiv-phone-02-clicking-build-with-autoreiv-opens-chat-on-autor.png`

## Findings
- None.

## Release note
- Capability gap cards in Agents Studio now show a single **Build with AutoReiv** action (plus **Dismiss**) that opens a new Chat session with AutoReiv pre-prompted with the capability gap details.
