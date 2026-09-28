# Findings

One line per finding, under the milestone it belongs to. Search this file and the open cards before adding (skill `card`, dedupe).
Sunday triage turns worthwhile findings into cards and deletes the rest with a reason.

Format: `- YYYY-MM-DD | area | symptom | from CARD-N | suspected files`

## M22 Clean baseline and process
- 2026-09-27 | tests | test_card539_selection_narrows.py takes ~21 s; it is an ADR-0061 guard, so it should be fast enough for the guard tier. Cause (CARD-560 profile): every resolve_allowed_tools/ToolPolicyGate call runs DataDirResolver().resolve(), which opens the live DB twice to peek settings (~5 ms per call, 2,400 calls); the same cost hits every tool-policy check at runtime | from CARD-559 | src/application/agent_packs/allowed_tools.py, src/infrastructure/data/resolver.py
- 2026-09-27 | tests | delete tests/unit/core/test_card_497_factory_backend_removal.py's Factory-pinned checks when CARD-498 lands (kept by CARD-560 while CARD-498 is Ready) | from CARD-560 | tests/unit/core/test_card_497_factory_backend_removal.py
- 2026-09-27 | preflight | the release tier's Playwright smoke stage is the largest (364 s, 73 tests); parallel pytest unit + integration is ~75 s | from CARD-560 | tests/e2e/smoke.spec.js, playwright.config.js
- 2026-09-27 | tests | test-value pass: 5 files use 192.168.1.29 as fake sample data (test_ollama_adapter, test_ui_agent_select_and_discovery, test_handoff_engine_kernel, test_log_buffer, test_system_agent_tools); plan: prune low-value card-pinned / fake-data tests during card triage | from CARD-560 | tests/unit
- 2026-09-27 | cards | list_card_status.py has no --milestone filter or priority column, and prints Complete/Completed/Done (Absorbed) as separate statuses | from CARD-559 | .agents/skills/card/scripts/list_card_status.py
- 2026-09-27 | live-qa | card-520 step 4 now shows CARD-535 as XFAIL instead of nudging; the step is nondeterministic (it passes when the approval lands before the reply ends), so an XPASS can happen before CARD-535 is fixed | from CARD-559 | tests/e2e/journeys/card-520-teach-needs-tool.mjs
- 2026-09-27 | live-qa | openSessionByTitle cannot open an API-created Tutor chat: after switching #agentSelect to tutor the drawer shows only the auto 'Tutor Chat' and the click times out; card-454 journey uses New Conversation instead | from CARD-454 | tests/e2e/journeys/lib/app.mjs, src/web/static/modules/studios/chat.js
