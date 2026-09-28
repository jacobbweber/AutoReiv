---
name: live-qa
description: Run a card's journeys on real models in a real browser, desktop and phone, in a throwaway env on :8770.
---
# Live QA

## Run
```powershell
.venv\Scripts\python.exe scripts/live_qa.py run --journeys card-556 --card CARD-556     #
.venv\Scripts\python.exe scripts/live_qa.py run --card ALL                               # all journeys (empty --journeys selects all)
```
- Serve on `127.0.0.1:8770` from a disposable worktree `<temp>\autoreiv-qa-checkout` with throwaway data in `scratch/live_qa_data`.
- Commit or `git add` new files first; the worktree copies tracked files only. Don't edit the repo during a run; exit code 3 means the real checkout changed.
- `--data clone` copies real AppData (read-only source, no `.vault_key`) when the card needs real agents or history.
- `--viewports desktop|phone`, `--keep`, `--out <dir>`.
- Model: `AUTOREIV_QA_VLLM_URL` / `AUTOREIV_QA_MODEL` (default nemotron-3.5-lightning at `http://192.168.1.218:8099/v1`).

## Endpoint check
- `run` first sends one chat completion (`max_tokens` 5, 20 s timeout) to the QA model. By hand:
  `.venv\Scripts\python.exe scripts/live_qa.py check-model`
- On failure the run exits 4 with `model endpoint down`. That is not a card failure: report it, wait, rerun.

## Retries
- Retry only on an endpoint failure (exit 4). Never rerun to get past model behaviour.
- `--attempts N` (default 1): a failed run is retried only when `check-model` then fails (endpoint down); a behaviour failure is never retried.

## Writing a journey
- One file per card: `tests/e2e/journeys/card-N-slug.mjs` exporting `{ id, card, title, allow, allowConsole, run(j, { page, request, base, viewport }) }`.
- `await j.step('What the operator does', fn, { timeoutMs })`: one screenshot per step. A step fails on a thrown error, a console error, a failed request not in `allow`, or a visible error banner.
- `clickExpect(locator, () => outcome, { label })` for every click. A click with no outcome is a "Dead button".
- Helpers: `tests/e2e/journeys/lib/app.mjs` (`openApp`, `openSessionByTitle`, `send`, `waitReplyIdle`, `jobStripText`, `sessionJobStatus`, `HITL_CARD`).
- Assert structure, never exact model text. Force the path where the model would choose.
- Known bug: `{ knownBug: 'CARD-N' }` on the step. It reports XFAIL; a pass reports XPASS and fails the run.
- `soft: true` requires `card: 'CARD-N'`; the runner rejects a soft step without it.
- No nudges, extra prompts or retries to get past a known bug.

## Report
- Folder: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-N\` (D: paths can't be attached): one screenshot per step, `summary.md`, `report.json`.
- Copy the results table and 2-3 screenshot paths into the card's Results section.
