# Findings

One line per finding, under the milestone it belongs to. Search this file and the open cards before adding (skill `card`, dedupe).
Sunday triage turns worthwhile findings into cards and deletes the rest with a reason.

Format: `- YYYY-MM-DD | area | symptom | from CARD-N | suspected files`

## M22 Clean baseline and process
- 2026-09-27 | tests | 104 unit files build and start the app per test: 566 tests, 425 s (66% of unit time) | from CARD-559 | tests/conftest.py, tests/unit/web/*
- 2026-09-27 | tests | test_openai_rate_limit_429 takes 14 s, likely real retry backoff | from CARD-559 | tests/unit/gateway/test_openai_adapter.py
- 2026-09-27 | tests | test_card539_selection_narrows.py takes 28.5 s; it is an ADR-0061 guard, so it should be fast enough for the guard tier | from CARD-559 | tests/unit/kernel/test_card539_selection_narrows.py
- 2026-09-27 | cards | list_card_status.py has no --milestone filter or priority column, and prints Complete/Completed/Done (Absorbed) as separate statuses | from CARD-559 | .agents/skills/card/scripts/list_card_status.py
- 2026-09-27 | tests | delete candidates from the test-suite review: Factory-pinned tests (test_factory_packs.py; test_card_497_* after CARD-498), overlaps with operator contracts (test_image_turn_gating_475.py, test_card502_adopt_persists.py) | from CARD-559 | tests/unit
- 2026-09-27 | live-qa | card-520 step 4 now shows CARD-535 as XFAIL instead of nudging; the step is nondeterministic (it passes when the approval lands before the reply ends), so an XPASS can happen before CARD-535 is fixed | from CARD-559 | tests/e2e/journeys/card-520-teach-needs-tool.mjs
- 2026-09-27 | preflight | the fast tier's changed-tests stage runs slow files too; a card touching 66 test files took 332 s (297 s in that stage) | from CARD-559 | .agents/skills/preflight/scripts/preflight.py
- 2026-09-27 | repo | scratch/ holds hundreds of stale files and folders from older cards (c4xx_*, c5xx_*, media, fake gateways); merge-to-qa only deletes the current agent's files | from CARD-454 | scratch/
- 2026-09-27 | live-qa | openSessionByTitle cannot open an API-created Tutor chat: after switching #agentSelect to tutor the drawer shows only the auto 'Tutor Chat' and the click times out; card-454 journey uses New Conversation instead | from CARD-454 | tests/e2e/journeys/lib/app.mjs, src/web/static/modules/studios/chat.js
