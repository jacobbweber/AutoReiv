---
id: CARD-532
title: "Live QA runner and a dedicated test environment: the coding assistant runs each card's live-test steps against a real serve with real models before handing the card to Jacob"
status: Ready
created: 2026-09-26
branch: qa
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

> **Status**: Ready (approved by Jacob 2026-09-26 ~4:40 PM ET). Coding-assistant tooling, not product: lives in `scripts/`, `tests/e2e/journeys/` and `.agents/`. CARD-533 builds the product feature on top of it.
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

## Decisions (open)

- **D1 Data:** throwaway-only vs optional clone of Jacob's real data. **Recommend both: throwaway by default, clone on demand.**
- **D2 Report location:** a fixed folder under `C:\Users\jacob\` (for example `C:\Users\jacob\AutoReivQA\<run-id>\`) vs configurable. **Recommend a configurable path defaulting to a `C:` folder.**
- **D3 Judge model:** on or off by default. **Recommend off.**

## Done when

`scripts` command starts the 8770 environment (throwaway or cloned), both first journeys run at desktop and phone with screenshots and a summary on `C:`, a dead button / console error / error banner each fail a step (tested), the live-qa skill and definition-of-done are updated, and no new dependencies were added.
