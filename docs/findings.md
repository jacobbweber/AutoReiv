# Findings

One line per finding, under the milestone it belongs to. Search this file and the open cards before adding (skill `card`, dedupe).
Sunday triage turns worthwhile findings into cards and deletes the rest with a reason.

Format: `- YYYY-MM-DD | area | symptom | from CARD-N | suspected files`

## M22 Clean baseline and process
- 2026-09-27 | tests | test_card539_selection_narrows.py takes ~21 s; it is an ADR-0061 guard, so it should be fast enough for the guard tier. Cause (CARD-560 profile): every resolve_allowed_tools/ToolPolicyGate call runs DataDirResolver().resolve(), which opens the live DB twice to peek settings (~5 ms per call, 2,400 calls); the same cost hits every tool-policy check at runtime | from CARD-559 | src/application/agent_packs/allowed_tools.py, src/infrastructure/data/resolver.py
- 2026-09-27 | tests | delete tests/unit/core/test_card_497_factory_backend_removal.py's Factory-pinned checks when CARD-498 lands (kept by CARD-560 while CARD-498 is Ready) | from CARD-560 | tests/unit/core/test_card_497_factory_backend_removal.py
- 2026-09-27 | preflight | the release tier's Playwright smoke stage is the largest (364 s, 73 tests); parallel pytest unit + integration is ~75 s | from CARD-560 | tests/e2e/smoke.spec.js, playwright.config.js
- 2026-09-27 | tests | Settings updates card has no first-paint Vitest contract (folded from CARD-452) | CARD-561 triage | src/web/static/modules/studios/settings*
- 2026-09-27 | updates | software-update auto scheduler defer-retry cadence and Windows restarter dry-run are unproven (folded from CARD-453) | CARD-561 triage | src/application/system/*update*
- 2026-09-27 | smoke | smoke TC-7 reads the Update button colour mid-transition and fails intermittently (folded from CARD-481) | CARD-561 triage | tests/e2e/smoke.spec.js
- 2026-09-27 | smoke | first click on a reply button right after sending (focused composer) can miss (folded from CARD-501) | CARD-561 triage | tests/e2e/smoke.spec.js
- 2026-09-27 | docs | steering/product.md and structure.md still describe "7 studios" (miss Skill, Tools, Education, Projects, Prompts) (folded from CARD-513) | CARD-561 triage | steering/product.md, steering/structure.md
- 2026-09-27 | logging | src.* INFO/WARNING log lines do not reach the serve log, so startup migrations cannot be checked from it (folded from CARD-528) | CARD-561 triage | src/web/app.py, scripts/restart_serve.ps1
- 2026-09-27 | agent-studio | Platform defaults badge seen empty after quickly switching agents (unconfirmed race) (folded from CARD-508) | CARD-561 triage | src/web/static/modules/studios/forge/platform_defaults.js
- 2026-09-27 | cards | list_card_status.py has no --milestone filter or priority column, and prints Complete/Completed/Done (Absorbed) as separate statuses | from CARD-559 | .agents/skills/card/scripts/list_card_status.py
- 2026-09-27 | live-qa | card-520 step 4 now shows CARD-535 as XFAIL instead of nudging; the step is nondeterministic (it passes when the approval lands before the reply ends), so an XPASS can happen before CARD-535 is fixed | from CARD-559 | tests/e2e/journeys/card-520-teach-needs-tool.mjs
- 2026-09-27 | live-qa | openSessionByTitle cannot open an API-created Tutor chat: after switching #agentSelect to tutor the drawer shows only the auto 'Tutor Chat' and the click times out; card-454 journey uses New Conversation instead | from CARD-454 | tests/e2e/journeys/lib/app.mjs, src/web/static/modules/studios/chat.js

## M24 Chat, jobs and tool reliability
- 2026-09-27 | jobs | reopening a chat whose job failed shows Failed without the reason and names the last queued phase (folded from CARD-536) | CARD-561 triage | src/web/static/modules/studios/chat*

## M25 Self-development
- 2026-09-27 | teach | reloaded Teach card still says "On for <agent>" after the skill is removed (folded from CARD-507) | CARD-561 triage | src/web/static/modules/studios/chat/render.js
- 2026-09-27 | developer | Developer reply can end with "Reply failed: The model returned an empty reply" right after registering a tool (folded from CARD-538) | CARD-561 triage | src/application/kernel/agent_kernel.py
- 2026-09-27 | jobs | Developer job strip shows Job failed next to a DONE phase while an attach proposal waits (folded from CARD-547) | CARD-561 triage | src/web/static/modules/studios/chat*
