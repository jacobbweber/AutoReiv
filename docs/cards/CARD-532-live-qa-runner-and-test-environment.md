---
id: CARD-532
title: "Live QA runner and a dedicated test environment: the coding assistant runs each card's live-test steps against a real serve with real models before handing the card to Jacob"
status: In Progress
created: 2026-09-26
branch: feat/card-532-live-qa-runner
related:
  - CARD-520
  - CARD-530
  - CARD-533
labels:
  - type:tooling
  - area:qa
  - area:coding-assistant
  - P1
---

# [CARD-532] Live QA runner + dedicated test environment

> **Status**: In Progress (refined and built 2026-09-26 ~6:40 PM ET on `feat/card-532-live-qa-runner` from qa `e28f5143` without waiting for `build`, per the new operating model: D1 was Jacob's, D2-D6 are technical). Approved by Jacob 2026-09-26 ~4:40 PM ET. Coding-assistant tooling, not product: lives in `scripts/`, `tests/e2e/journeys/` and `.agents/`. CARD-533 builds the product feature on top of it.
> **Related**: CARD-520 (first journey), CARD-530 (second journey), CARD-533 (AutoReiv-side journey testing)
> **Labels**: `type:tooling`, `area:qa`, `area:coding-assistant`, `P1`

## Why

Every card so far has been handed to Jacob with a runbook he walks by hand, and his live tests keep finding what mocked tests miss (CARD-520 rounds 1 and 2: a reasoning model spending all tokens thinking, a tool registered with no grant, an Approve click that killed the turn). Grok Bot (the coding assistant) should walk those same steps itself, against a real AutoReiv serve with real models (vLLM / Ollama, no mocked LLM), and hand Jacob a card only after its journeys pass, with screenshots.

## Acceptance criteria (EARS)

- **REQ-532-001 Journey files:** Each card MAY have a journey file in the repo (`tests/e2e/journeys/<card>-<name>.*`). A journey is an ordered list of steps (click, type, wait-for) with assertions on UI state, DB rows, job/phase status and serve log lines. Journeys stay in the repo as regression tests.
- **REQ-532-002 Real clicks that fail loudly:** WHEN a step clicks a button, THE runner SHALL click the real element AND fail the step if the expected outcome (element, text, request, DB row) does not follow within the step timeout (catches dead buttons).
- **REQ-532-003 Error watchers:** WHILE a journey runs, THE runner SHALL fail the step on any browser console error, failed network request (4xx/5xx or network error, with an allowlist per journey), or visible error banner ("Reply failed", toast of type error).
- **REQ-532-004 Evidence:** THE runner SHALL save a screenshot per step and write a pass/fail report plus a short summary file (journey, step, result, reason, screenshot path) to an output folder readable from `C:` (Grok Bot's Read/CopyToBox refuse `D:` paths). Default under `C:\Users\jacob\...` (see D2), configurable.
- **REQ-532-005 Viewports:** Each journey SHALL run at desktop and phone viewports (phone optional per step when the UI differs).
- **REQ-532-006 Dedicated environment:** THE runner SHALL start its own serve on a separate port (default 8770) with a throwaway data folder (`AUTOREIV_DATA_DIR` override, as `scripts/smoke_server.py` already does), never Jacob's `%LOCALAPPDATA%\AutoReiv` or port 8000.
- **REQ-532-007 Data commands:** One command SHALL clone Jacob's real AppData into the test data folder (copy, never write back); one command SHALL seed or reset mock data (fixtures such as the CARD-520 friction seed).
- **REQ-532-008 Real models:** The test serve SHALL use the configured real providers (vLLM `nemotron-3.5-lightning` at 192.168.1.218:8099, Ollama). Assertions on model replies SHALL be structural (a card appears, a job reaches `done`, a tool is granted), not exact text.
- **REQ-532-009 No new dependencies:** THE runner SHALL reuse the existing browser automation (Playwright, `@playwright/test` already in `package.json`, used by `tests/e2e/smoke.spec.js`). No new external packages or services.
- **REQ-532-010 Optional judge (off by default):** WHERE enabled, a local-model judge (Spark vLLM, its own model config, separate from the product's) MAY grade non-deterministic replies against a rubric in the journey; its verdict and reasoning go in the report.
- **REQ-532-011 First journeys:** (a) CARD-520: Teach on "weather in Boston" -> Needs a tool -> Ask Developer to build this tool -> the tool is granted to autoreiv -> AutoReiv answers the weather question. (b) CARD-530: approve a HITL card while the Developer reply is still streaming -> one turn, one reply, job `done`, no "Reply failed" (expected red until CARD-530 ships).
- **REQ-532-012 Workflow:** Add an `.agents` skill (`.agents/skills/live-qa/SKILL.md`: how to start the environment, run journeys, read the report, send screenshots). Update the card workflow (`.agents/rules/definition-of-done.md` and the card-status / SDD walk) so Grok Bot runs the card's journeys before setting a card to In Review and sends Jacob the screenshots and summary.

## Out of scope (for now)

- Tailscale or visual (pixel/OS-level) clicking.
- Hyper-V or Docker isolation.
- Product-side journey testing (CARD-533).

## Four Beats

1. **What Jacob means:** he is product owner, not the live tester. Before a card reaches him, the coding assistant has already walked its live-test steps in a real browser against a real AutoReiv with real models, on desktop and phone, and hands him the results and 2-3 screenshots.
2. **What AutoReiv does now:** only the mocked Playwright smoke suite (`tests/e2e/smoke.spec.js`, scratch data on :8765, routed LLM answers) and ad-hoc scratch scripts (`scratch\c530_browser_qa.mjs`, `scratch\c505_serve.py` on :8767) that are not in the repo and not reusable.
3. **What will change:** `scripts/live_qa.py` (env on :8770: throwaway by default, `--data clone` on demand, real vLLM provider, one-command `run`), `tests/e2e/journeys/lib/runner.mjs` (steps, screenshots, dead-button / console / failed-request / error-banner watchers, report + summary, optional judge), `tests/e2e/journeys/lib/app.mjs` (SPA helpers), `tests/e2e/journeys/run.mjs` (CLI on the existing `@playwright/test` chromium), journeys `card-520-teach-needs-tool.mjs` and `card-530-approve-mid-stream.mjs`, skill `.agents/skills/live-qa/SKILL.md`. The workflow rules already say the assistant live-tests (governance commit `e28f5143`); the DoD and SDD walk point at this runner.
4. **What dies today:** the ad-hoc scratch browser script `scratch\c530_browser_qa.mjs` and the c530 scratch clone (removed after CARD-530 merged; the runner replaces them). Nothing in `src/` changes.

## Decisions (resolved 2026-09-26)

- **D1 Data:** Jacob decided: throwaway by default (`scratch/live_qa_data`, wiped each start), clone of the real AppData on demand (`--data clone`: copy only, no `.vault_key`, the copy's `wiki_path` / `data_dir` repointed into the copy).
- **D2 Report location (technical, recommendation taken):** configurable (`AUTOREIV_QA_REPORT_DIR` or `--out`), default `<temp>\autoreiv-qa\<card>\` = `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-N\` on Jarvis.
- **D3 Judge (technical, recommendation taken):** off by default; `--judge` with `AUTOREIV_QA_JUDGE_URL` / `AUTOREIV_QA_JUDGE_MODEL`.
- **D4 (technical):** a throwaway env gets the real vLLM provider through the sanctioned `POST /api/settings/providers` after start (`AUTOREIV_QA_VLLM_URL` / `AUTOREIV_QA_MODEL` override).
- **D5 (technical):** model behaviour outside a card's scope is a soft step (warning, journey continues); the CARD-520 journey nudges the Developer with "Approved. Please continue..." when it stops after an approval (known CARD-535) and records it.
- **D6 (technical):** `--attempts N` retries a journey whose model run did not produce the state under test (for example no draft filed, so no mid-stream card); every attempt is kept in the report.

## Failing-tests-first plan

- `tests/unit/scripts/test_card532_live_qa.py`: port 8770 default and 8000 refused; data dir under scratch passes the CARD-467 guard, inside live AppData refused; clone copies without `.vault_key`, never writes to the source, repoints `wiki_path`; overlapping folders refused; real vLLM provider payload with overrides; runner command (port, journeys, viewports, judge off by default); `start(8000)` refused before touching anything.
- `tests/unit/frontend/live_qa_runner_532.test.js`: report folder default + override; viewports; dead button fails loudly and stops the journey; console error, disallowed failed request, error banner / error toast each fail a step; soft step = warning; screenshot per step; summary rows; judge off by default; both journey files exist and are not smoke specs; no new dependencies.

## Done when

`scripts` command starts the 8770 environment (throwaway or cloned), both first journeys run at desktop and phone with screenshots and a summary on `C:`, a dead button / console error / error banner each fail a step (tested), the live-qa skill and definition-of-done are updated, and no new dependencies were added.
