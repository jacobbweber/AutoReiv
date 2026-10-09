---
id: CARD-661
title: "1.0 gate — Written acceptance checklist run once on a clean data folder"
type: feature
status: Done
priority: P1
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/test_card661_acceptance_checklist.py]
branch: docs/card-661-acceptance-checklist
log: {minutes: 45, qa_runs: 1, findings: 0}
created: 2026-10-06
completed: 2026-10-09
related:
  - CARD-658
  - CARD-659
  - CARD-660
  - CARD-662
  - CARD-663
  - CARD-664
  - CARD-665
  - CARD-666
  - CARD-667
  - CARD-668
---

# CARD-661 1.0 gate — Written acceptance checklist run once on a clean data folder

## 1.0 gate set
This card is part of the AutoReiv 1.0 gate set: CARD-658, CARD-659, CARD-660, CARD-661, CARD-662, CARD-663, CARD-664, CARD-665, CARD-666, CARD-667, CARD-668.
Do not start work until Jacob approves a build for this card.


## Intent
1.0 needs one written acceptance checklist that covers a fresh install through the main operator paths, and proof that checklist was run once against a clean data folder.

## Goal
There is a short written checklist (fresh install → chat → wiki → a course step → a skill toggle → a routine → restart and confirm persistence). Someone runs it once on a clean data folder and records pass/fail on this card.

## Acceptance
- Checklist is written in plain full words (this card or a linked doc under docs/).
- Steps cover at least: fresh install, a real chat, a wiki action, one course step, toggling a skill in Agent Studio, running or confirming a routine, restart, and confirming the earlier work is still there.
- The checklist is run once on a clean data folder; results are recorded on this card (pass/fail per step, date, environment).

## Plan and decisions
Jacob approved the build on 2026-10-09. Prefer a throwaway data folder so live data is never wiped for the run.

## Checklist
`docs/acceptance-checklist-1.0.md`: setup on a throwaway data folder, then eight steps (fresh install, real chat, wiki action, course step, skill toggle in Agent Studio, routine, restart, persistence) with a "pass when" for each.

## Run (2026-10-09, about 12:05 to 12:10 ET)
Environment: Jarvis (Windows 11), fresh clone of qa `10135412` in `%TEMP%\ar10\clone661`, new empty data folder `%TEMP%\ar10\data661`, serve on 127.0.0.1:8790. Model: Spark vLLM `http://192.168.1.218:8006/v1` `nemotron-3.5-lightning`, the only model it serves (no model load or swap). Every agent was on the default model. The steps were driven through the same HTTP API the UI uses (Agent Studio save = `PUT /api/agents/{id}` with `allowed_skill`).

| # | Step | Result | Notes |
|---|---|---|---|
| 1 | Fresh install | PASS | Health 200; `database/`, `wiki/`, `agents/`, `skills/` created. |
| 2 | Real chat | PASS | Session `38cc37c0-...`: the answer streamed back and the session holds its messages. Quality finding: 14 tool calls and a wrong answer (CARD-680). |
| 3 | Wiki action | PASS | `00_Inbox/checklist_note_661.md` created and reopened. |
| 4 | Course step | PASS | Course `course_43fb016d9a9a`: `priming -> retrieval`. |
| 5 | Skill toggle | PASS | `worker` turned off for `autoreiv` (10 -> 9 skills). |
| 6 | Routine | PASS | `checklist-661` created (disabled schedule) and run once: status success. |
| 7 | Restart | PASS | Stopped by exact command line, started again on the same data folder: health 200. |
| 8 | Persistence | PASS | Chat, note, course step, skill change and routine run all still there. |

**Verdict: PASS.**

Left in place on purpose (gate-test leftovers, not deleted): `%TEMP%\ar10\clone661`, `%TEMP%\ar10\data661`.
