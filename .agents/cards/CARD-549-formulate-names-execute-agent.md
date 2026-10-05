---
id: CARD-549
title: "Formulate on AutoReiv should know the Execute phase is on Developer"
status: Done (Superseded by CARD-554)
completed: 2026-10-05
created: 2026-09-27
branch: qa
related:
  - CARD-544
  - CARD-546
labels:
  - type:bug
  - area:orchestration
  - P3
superseded_by: CARD-554
needs_decision: none
---

# [CARD-549] Formulate should name the agent that runs Execute

> **Status**: Done (Superseded by CARD-554)
> **Related**: CARD-544, CARD-546
> **Labels**: `type:bug`, `area:orchestration`, `P3`

## Evidence

In one phone run of the routing journey, AutoReiv's Formulate reply for a code request read "I cannot execute this request directly. The `execute_code` skill (and `write_project_file`) are not ticked..." even though the Execute phase was assigned to Developer. Other runs planned normally. The reply reads like a refusal and confuses the operator.

## Change

Put the Execute phase's assigned agent in the phase working set (`build_phase_working_set` / `format_phase_working_set_prompt`), for example "Execute runs on Developer; plan for it, do not run it." A unit test checks that the Formulate prompt names the Execute agent when it differs from the chat agent.

## Done when

The unit test passes, and three runs of the routing journey show no "cannot execute" wording in Formulate.

## Note (2026-09-27, from CARD-554)

This is largely covered by the CARD-554 planning block. A planning phase's assignment now says "plan only" and names the agent that runs each later phase (`format_planning_phase_block` in `src/application/orchestration/phase_roles.py`), and the tool gate blocks work tools and handoff in Formulate. In the four card-550 runs and two card-539 runs on `feat/card-554-553-phase-handoff-tools`, Formulate replied with a plan and no "cannot execute" wording. The card stays Ready until the three routing-journey runs in "Done when" are recorded after merge.
