---
id: CARD-680
title: "Fresh install: a plain 'what is X in AutoReiv' question makes 14 tool calls and answers wrong"
type: bug
status: Ready
priority: P2
milestone: M23
needs_decision: build
proof:
  journeys: []
  checks: []
branch:
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-09
completed:
related:
  - CARD-661
---

# CARD-680 Fresh install: a plain "what is X in AutoReiv" question makes 14 tool calls and answers wrong

## Backlog
Found in the CARD-661 checklist run on 2026-10-09 (fresh data folder, Spark vLLM nemotron-3.5-lightning, throwaway :8790). Not started; needs Jacob's build approval.

## Problem
Asked "In two short sentences, what is a standing Job in AutoReiv?" on a fresh install, AutoReiv made 14 tool calls (system info, health, wiki search and list several times, its own agent profile, logs). The wiki repeat guard stopped it ("you already looked in the wiki 8 times"). It then answered wrongly: "a recurring or persistent scheduled task ... RoutineScheduler, DataDirBackupScheduler, SoftwareUpdateScheduler". A standing Job is a goal run in phases (Formulate, then Execute) with a done-when.

The checklist step still passed (an answer streamed and was saved), but a new user's first question is slow and wrong.

## Cause (to confirm)
- A fresh wiki has no notes about AutoReiv itself, so the search finds nothing and the model keeps looking, then guesses from logs.
- The agent has no short built-in description of AutoReiv's own concepts (Jobs, phases, routines, skills) to answer from.

## Change (proposal)
- Give the primary agent a short, fixed "AutoReiv concepts" block (or a seeded read-only wiki note) so product questions are answered without tools.
- Consider a lower repeat limit for wiki search on a turn that found nothing.

## Proof
- Lean live: on a fresh data folder the same question is answered correctly with at most 2 tool calls.
