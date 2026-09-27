---
id: CARD-544
title: "Untick coding on AutoReiv so code work routes to Developer"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-539
labels:
  - type:bug
  - area:agents
  - P2
---

# [CARD-544] Untick coding on AutoReiv so code work routes to Developer

> **Status**: Ready. D1 decided by Jacob on 2026-09-26: untick `coding` on AutoReiv, and route code work to Developer. Implementation not started.
> **Related**: CARD-539 (ADR-0061), CARD-546
> **Labels**: `type:bug`, `area:agents`, `P2`

## Why

CARD-539 section 9.2 expects a code request to AutoReiv to be handed off to Developer. The seeded AutoReiv pack ticks `coding` (`repo_file_read`, `repo_file_list`, `repo_file_write`, `repo_file_patch`). Under ADR-0061 that puts code requests inside AutoReiv's domain. Live QA saw AutoReiv plan a job and ask for approval of `repo_file_write` itself instead of handing off. AutoReiv's pack prompt already says to hand shell and software-engineering work to Developer, so the tick contradicts the prompt.

## Decisions

| # | Decision | Choice | Decided |
|---|---|---|---|
| D1 | Should AutoReiv keep `coding` ticked? | **No.** Untick `coding` on AutoReiv. Code work (reading, writing or patching repo files, running code) routes to Developer with `handoff_to_agent`. | Jacob, 2026-09-26 |

## Requirements (EARS)

- **REQ-544-001**: THE SYSTEM SHALL ship the AutoReiv platform pack (`platform-packs/autoreiv/pack.json`) without `coding` in `allowed_skill`.
- **REQ-544-002**: WHEN the app starts on data where the stored AutoReiv profile still ticks `coding` THE SYSTEM SHALL untick it once through a real, idempotent migration. The migration writes a backup of the old skill list, records a marker, goes through the shared skill save path so platform promotion keeps the change, and changes nothing on a second run. The operator can tick `coding` again in Agent Studio afterwards, and later runs must not remove it.
- **REQ-544-003**: WHILE `coding` is not ticked for AutoReiv, `resolve_allowed_tools(autoreiv)` SHALL contain no `repo_file_*` tool, and the generated domain line SHALL not list Coding.
- **REQ-544-004**: WHEN AutoReiv receives a code request THE SYSTEM SHALL hand it off to Developer (`handoff_to_agent`), with no refusal text and without AutoReiv calling a `repo_file_*` tool.

## Tests (write first, confirm red)

- Unit: the shipped AutoReiv pack does not tick `coding`, and the resolver set for AutoReiv has no `repo_file_*` tool.
- Migration covers four cases:
  - A stored profile that ticks `coding` loses it, and a backup plus a marker are written.
  - A second run changes nothing.
  - A later operator re-tick survives both a restart and platform promotion.
  - A fresh install is untouched.
- Live QA, journey `card-539-out-of-domain-routing`, restored to the CARD-539 section 9.2 form:
  - Step 1: a code request to AutoReiv (for example, write and run a small Python function) produces a `handoff_to_agent` row to Developer, and the reply has no refusal text.
  - The Tutor due-review probe stays as an extra step.
  - Run on desktop and phone.

## Done when

- The pack and the stored AutoReiv profile no longer tick `coding`.
- The migration is tested.
- The restored routing journey hands the code request to Developer on desktop and phone. Model flakiness is tracked in CARD-546.
- CHANGELOG `[Unreleased]` is updated.