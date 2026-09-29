# [ADR-0063] A Standing Job Starts Only When Asked

> **Status**: Accepted  
> **Date**: 2026-09-29  
> **Deciders**: Jacob Weber (Product Owner), coding assistant  
> **Related Cards**: [CARD-572](../../.agents/cards/CARD-572-explicit-job.md) (implementation), CARD-565, CARD-564, CARD-215, CARD-222, CARD-230, CARD-271  
> **Reverses**: CARD-215 REQ-JOBGRAPH-001a ("runtime decides; no Chat toggle or request flag") and the CARD-230 outcome-shaped routing

---

## 1. Context

Chat and routines decided "normal turn or two-phase standing Job" by matching the message text: numbered lines,
first/then/finally, deliverable verbs with "that/when", wiki/note writes, done-when, stated criteria
(`is_multi_step_outcome`, `_GOAL_DELIVERABLE`, `route_standing_chat`). Ordinary asks became Jobs (CARD-564 round 1:
"review CARD-3 against its acceptance criteria"; CARD-565 narrowed one phrase). Jacob could not tell which way a
message would go. Other harnesses (Hermes, OpenClaw, OpenHuman, Odysseus) start long work from an explicit action or a
tool the model chooses, never from a regex on the user's message.

## 2. Decision

1. A Chat message becomes a standing Job only when the **Run as a job** box (beside Auto-run in Chat options) is
   ticked. The request carries `run_as_job: true`. The box is off by default, never remembered, and unticks after each send.
2. A routine runs as a standing Job only when its own **Run as a job** setting (`metadata.run_as_job`) is on. Default off.
   The prompt is never scanned.
3. The keyword router is deleted: `route_standing_chat`, `StandingRoute`, `is_multi_step_outcome`, `is_outcome_shaped`,
   `_GOAL_DELIVERABLE`. The dead `goal_mode` request field is removed. A guard test fails if any of them return.
4. Explicit callers that exist to start a Job (Education Ask and pressure ask) send `run_as_job: true`.
5. Existing routines are not migrated (no migrations before 1.0); Jacob ticks the ones he wants.

## 3. Consequences

- Predictable: nothing becomes a Job without a click. A multi-step ask sent normally is one ReAct turn in the chat itself.
- Jacob must tick the box for work he wants planned and run in phases; the built-in Weekly Note Rollover routine,
  which ran as a Job only because of its wording, now runs as one turn until its box is ticked.
- `derive_success_rule` / `is_testable_success_rule` stay: they shape the Job once one is started.
