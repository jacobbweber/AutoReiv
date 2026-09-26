---
name: live-qa
description: >-
  Run a card's live-test journeys yourself before In Review: a dedicated AutoReiv serve on :8770
  (throwaway data by default, clone of the real AppData on demand), real models, real browser clicks
  at desktop 1280x800 and phone 390x844, screenshots and a summary on a C: path for the review check-in.
---

# Live QA (CARD-532)

Jacob is product owner, not the live tester (operating model 2026-09-26, `AGENTS.md`). The coding assistant runs every card's live-test steps with this runner, fixes what fails, files Ready cards for out-of-scope findings, and sends the review check-in with 2-3 screenshots.

## One command

```powershell
python scripts/live_qa.py run --journeys card-520,card-530 --card CARD-532
```

- Starts its own serve on `127.0.0.1:8770` (never 8000) with throwaway data in `scratch/live_qa_data` (wiped each start), points it at the real vLLM (`nemotron-3.5-lightning` at `192.168.1.218:8099`; override with `AUTOREIV_QA_VLLM_URL` / `AUTOREIV_QA_MODEL`), runs the journeys at desktop and phone, writes the report, stops the serve.
- `--data clone`: copies `%LOCALAPPDATA%\AutoReiv` into `scratch/live_qa_data` first (read-only on the source; `.vault_key` not copied; the copy's `wiki_path` / `data_dir` point at the copy). Use when a card needs Jacob's real agents, jobs or history.
- `--viewports desktop` or `phone`, `--attempts 2` (retry a journey whose model run did not produce the state under test), `--keep` (leave :8770 up), `--out <dir>`, `--judge` (optional local-model judge, off by default; `AUTOREIV_QA_JUDGE_URL` / `AUTOREIV_QA_JUDGE_MODEL`).
- Env only: `python scripts/live_qa.py start [--data clone]`, `stop`, `status`, `reset`, `clone`.
- Runner only (env already up): `node tests/e2e/journeys/run.mjs --base http://127.0.0.1:8770 --journeys card-530 --viewports desktop,phone`.

## Report

Default folder: `AUTOREIV_QA_REPORT_DIR`, else `<temp>\autoreiv-qa\<card>\` (on Jarvis `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-N\`; D: paths cannot be attached). It holds one screenshot per step (`<journey>-<viewport>-NN-<step>.png`), `summary.md` (journey, viewport, step, result, reason, screenshot) and `report.json` (plus console errors, failed requests, notes).

## Writing a journey

One file per card journey: `tests/e2e/journeys/card-<N>-<name>.mjs` exporting `{ id, card, title, allow, allowConsole, run(j, { page, request, base, viewport }) }`. Journeys stay in the repo as regression tests (not picked up by the smoke suite).

- `await j.step('What the operator does', async () => { ... }, { timeoutMs, soft })`: a screenshot per step. A step fails on a thrown error, a console error, a failed request not in `allow`, or a visible error banner (`.chat-stream-error`, error toast, "Reply failed"). A failure stops the journey; `soft: true` records a warning and continues (use for model behaviour outside the card's scope).
- `clickExpect(locator, () => outcome, { label, what, timeoutMs })` for every click: a click with no outcome is a "Dead button" failure.
- Helpers in `tests/e2e/journeys/lib/app.mjs`: `openApp`, `openSessionByTitle`, `send`, `waitReplyIdle`, `trackStreams`, `jobStripText`, `sessionJobStatus`, `HITL_CARD`.
- Assert model replies structurally (a card appears, a job reaches done, a tool is granted or called), never exact text.

## Check-in to Jacob

Card In Review, then: what changed, what was tested (journeys and preflight), results table from `summary.md`, open items and new cards, 2-3 best screenshot paths. Merge only after **merge to qa**.
