---
id: CARD-554
title: "Formulate does the work itself, then ends FAILED after a completed handoff; Execute stays queued"
status: Ready
created: 2026-09-27
branch: qa
related:
  - CARD-549
  - CARD-551
  - CARD-550
labels:
  - type:bug
  - area:orchestration
  - P3
---

# [CARD-554] Formulate fails after a completed handoff and Execute never starts

> **Status**: Ready (filed from CARD-550 live QA, 2026-09-27 ET).
> **Related**: CARD-549 (Formulate should name the Execute agent), CARD-551, CARD-550
> **Labels**: `type:bug`, `area:orchestration`, `P3`

## Evidence

For a code ask in an AutoReiv chat, the job's Execute phase was correctly assigned to Developer. Instead of planning, AutoReiv's Formulate phase tried to do the work itself:

- `repo_file_read` was blocked by policy (expected, since AutoReiv has no `coding`).
- Several `activate_skill` calls were refused.
- It then called `handoff_to_agent` to Developer from inside the Formulate phase.

The handoff completed, but Formulate ended FAILED on desktop. On phone it sat waiting for approval. In both runs Execute (Developer) stayed queued and never ran. In the final runs, both desktop and phone ended FAILED. The chat banner reads: "Job failed: Another run of this job changed this step while it was finishing, so it could not be recorded. The job was stopped so it does not hang". The handoff result row shows `parent_job_id=job_... child_job_id=job_...` with the same id. So the handoff child writes to the parent's job, and Formulate's own completion then loses the step-version check. The likely cause is that the child shares the job id instead of getting its own (or none).

## Change

Formulate should plan only, and must not call work tools or handoff. Also, a completed handoff inside a phase should not mark the phase FAILED. CARD-549's working-set line ("Execute runs on Developer; plan for it, do not run it") covers part of this. This card adds the phase-status fix and a unit test for it: a Formulate phase whose handoff child completes ends DONE, and Execute becomes runnable.

## Done when

The unit test passes. In three runs of the CARD-550 code ask, the Developer Execute phase starts.
