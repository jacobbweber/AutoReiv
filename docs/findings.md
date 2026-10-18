# Findings

One line per finding, under the milestone it belongs to. Search this file and the open cards before adding (skill `card`, dedupe).
Sunday triage turns worthwhile findings into cards and deletes the rest with a reason.

Format: `- YYYY-MM-DD | area | symptom | from CARD-N | suspected files`

## M22 Clean baseline and process
- 2026-09-27 | preflight | the release tier's Playwright smoke stage is the largest (364 s, 73 tests); parallel pytest unit + integration is ~75 s | from CARD-560 | tests/e2e/smoke.spec.js, playwright.config.js
- 2026-09-27 | tests | Settings updates card has no first-paint Vitest contract (folded from CARD-452) | CARD-561 triage | src/web/static/modules/studios/settings*
- 2026-09-27 | updates | software-update auto scheduler defer-retry cadence and Windows restarter dry-run are unproven (folded from CARD-453) | CARD-561 triage | src/application/system/*update*
- 2026-09-27 | smoke | smoke TC-7 reads the Update button colour mid-transition and fails intermittently (folded from CARD-481) | CARD-561 triage | tests/e2e/smoke.spec.js
- 2026-09-27 | smoke | first click on a reply button right after sending (focused composer) can miss (folded from CARD-501) | CARD-561 triage | tests/e2e/smoke.spec.js
- 2026-09-27 | logging | src.* INFO/WARNING log lines do not reach the serve log, so startup migrations cannot be checked from it (folded from CARD-528) | CARD-561 triage | src/web/app.py, scripts/restart_serve.ps1
- 2026-09-27 | cards | list_card_status.py has no --milestone filter or priority column, and prints Complete/Completed/Done (Absorbed) as separate statuses | from CARD-559 | .agents/skills/card/scripts/list_card_status.py
- 2026-09-27 | live-qa | card-520 step 4 still labels its idle stop knownBug 'CARD-535', but CARD-535 was closed as obsolete in CARD-577; drop or re-point the knownBug when the journey is next touched | from CARD-559, updated CARD-577 | tests/e2e/journeys/card-520-teach-needs-tool.mjs
- 2026-09-27 | live-qa | openSessionByTitle cannot open an API-created Tutor chat: after switching #agentSelect to tutor the drawer shows only the auto 'Tutor Chat' and the click times out; card-454 journey uses New Conversation instead | from CARD-454 (recheck Tutor journey after CARD-562) | tests/e2e/journeys/lib/app.mjs, src/web/static/modules/studios/chat.js

## M24 Chat, jobs and tool reliability
- 2026-09-29 | hitl | /api/hitl/decide saves the approved tool's result row in both the phase session and the parent chat session (left over when CARD-557 closed) | from CARD-577 | src/web/routers/hitl.py
- 2026-09-29 | settings | POST /api/settings/matrix silently turns max_concurrent_generations outside 1-3 into 1 (sent 4, saved 1, no error); clamp to 3 or return 400 | from battery 2026-09-29 | src/web/routers/settings.py
- 2026-09-29 | chat | /api/chat/stream accepts any approval_mode; only 'run' auto-approves and anything else (e.g. 'auto') silently means ask, so scripts that send 'auto' get approval parks with no hint | from battery 2026-09-29 | src/application/kernel/tool_registry.py, src/web/routers/chat.py

## M25 Self-development
- 2026-09-27 | teach | reloaded Teach card still says "On for <agent>" after the skill is removed (folded from CARD-507) | CARD-561 triage | src/web/static/modules/studios/chat/render.js
- 2026-09-28 | live-qa | the journey hangs (instead of failing) when the chat stream returns an error event before any reply | from CARD-562 | tests/e2e/journeys/card-562-developer-one-card-to-in-review.mjs
- 2026-09-29 | tests | 5 legacy capability-authoring / MCP-building tests stay skipped (commit_skill, agent builder job phase, MCP dev deploy, oc428, oc429) | from CARD-571 | tests/unit/orchestration, tests/integration/mcp, tests/integration/operator_contracts
