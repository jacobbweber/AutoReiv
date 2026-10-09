---
id: CARD-680
title: "Fresh install: a plain 'what is X in AutoReiv' question makes 14 tool calls and answers wrong"
type: bug
status: Done
priority: P2
milestone: M23
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/kernel/test_card680_product_concepts.py]
branch: fix/card-680-product-concepts
log: {minutes: 30, qa_runs: 1, findings: 0}
created: 2026-10-09
completed: 2026-10-09
related:
  - CARD-661
---

# CARD-680 Fresh install: a plain "what is X in AutoReiv" question makes 14 tool calls and answers wrong

## Backlog
Found in the CARD-661 checklist run on 2026-10-09 (fresh data folder, Spark vLLM nemotron-3.5-lightning, throwaway :8790). Jacob approved the build on 2026-10-09.

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

## Root cause
Nothing told an agent what AutoReiv's own concepts are. A fresh wiki has no notes about AutoReiv, so asked "what is a standing Job?" the agent searched the wiki, its profile, health and logs (14 calls) until the wiki repeat guard stopped it, then guessed from scheduler names in the logs.

## Fix
`src/domain/agents/product_concepts.py` holds a short, fixed "About AutoReiv" block (Chat, standing Job, Routine, Agent, Skill, Wiki, Education, capability gap, data folder), with the instruction to answer questions about AutoReiv itself from it without tools. The kernel adds it to every agent's system message (shipped and user agents, so an edited copy of an agent still gets it). About 1.4k characters. The wiki repeat limit was left as it is (relaxed limits).

## Checks
`tests/unit/kernel/test_card680_product_concepts.py` failed first (no concepts module) and passes now (7 tests: a standing Job is a goal run in phases Formulate/Execute with Run as a job, distinct from a Routine; says "without tools"; stays short; present for autoreiv, tutor, direct and a user agent, after the agent's own prompt).

Live on Jarvis, 2026-10-09: fresh data folder, throwaway :8790 from the worktree, Spark :8006 nemotron-3.5-lightning only. "In two short sentences, what is a standing Job in AutoReiv?" and "What is a standing Job?" were both answered correctly with 0 tool calls (was 14 calls and a wrong answer). The :8790 serve was stopped by exact command line.
