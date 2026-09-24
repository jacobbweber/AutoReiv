---
id: CARD-462
title: "Per-reply time limit and separate turn budgets for chat vs standing Jobs"
status: Ready
created: 2026-09-24
branch: qa
adr: none
related:
  - CARD-445
  - CARD-460
  - CARD-461
labels:
  - type:feature
  - area:kernel
  - area:jobs
  - area:chat
  - P2
---

# [CARD-462] Per-reply time limit and separate turn budgets for chat vs standing Jobs

> **Status**: Ready (needs Jacob's numbers - see "Open decisions" - before **build**)
> **Created**: 2026-09-24
> **Observed during**: CARD-445 discussion - Jacob asked for ideas beyond a turn count: a time limit per reply, and different budgets for interactive chat vs standing Jobs.
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:kernel`, `area:jobs`, `area:chat`, `P2`
> **Related**: [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) (default 50), [CARD-460](./CARD-460-kernel-repeat-guard-reuse-result-before-stop.md), [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md) (graceful ending path reused here)

**Why one card:** both items are the same "limits for one run" policy, enforced at the same point (the kernel's per-reply loop guard) and ending through the same CARD-461 helper. If Jacob wants them apart, split at **continue** (time limit first).

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Lock the numbers / split the card - **still no product code** |
| **`build`** | Implement the time limit and job budget test-first |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md) (summary ending) and [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) (agent default 50) |
| **Blocked by** | Jacob's numbers (Open decisions) |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. A single chat reply should not be able to run for ages. If it takes too long, it should stop and tell me what it did, the same polite way as the turn limit.
2. Background standing Jobs are different from me chatting: they may deserve their own step budget, and that budget should actually work instead of being a number nobody reads.

### Beat 2: What AutoReiv does now

1. **Chat replies have no wall-clock limit.** Only `max_turns` (the agent's profile value) bounds a reply in `agent_kernel.py`.
2. **Standing Job phases have a per-model-call timeout, not a per-reply one:** `phase_llm_resilience.STANDING_PHASE_LLM_TIMEOUT_SECONDS = 300.0`, overridable by env `STANDING_PHASE_LLM_TIMEOUT_SECONDS` (`resolve_standing_phase_llm_timeout`), used from `web/routers/chat.py` (~L547-630), `routines/executor.py:157` and `standing_job_graph.py`. A phase with many fast calls can still run indefinitely up to the turn cap.
3. **Job / phase turn budgets exist but nothing enforces them:**
   - `domain/orchestration/models.py`: `Phase` / `PhaseSpec` `max_turns=10` (L175-184, 212, 245-247, 304, 410);
   - `job_phase_orchestrator.py:179` builds specs with `max_turns=10` and passes `spec.max_turns` through (L219, 236, 467, 483); `followup.py:114` copies it;
   - `phases.max_turns INTEGER NOT NULL DEFAULT 10` (schema L38);
   - the kernel ignores all of these and loops `range(agent.max_turns)`.
4. **Handoffs:** `HandoffEnvelope.max_turns=10`, `timeout_seconds=60.0` (models.py L43-44). Children get `bound_child_max_turns(envelope.max_turns, profile.max_turns)` (`handoff_engine.py:329`). `timeout_seconds` appears unused in orchestration (verify at build).

### Beat 3: What will change

1. **Per-reply time limit (chat).** A wall-clock limit per reply, checked at each loop pass and before each tool call. When it passes, end through CARD-461's helper with reason `time_limit` ("I ran out of time for one reply..."). An in-flight model call or tool is not killed mid-way; the check happens between steps. Global setting in Settings, default per Open decision 1.
2. **Per-run time limit (standing Jobs).** The same check for phase runs, with its own setting (Open decision 2). The existing per-call `STANDING_PHASE_LLM_TIMEOUT_SECONDS` stays as-is.
3. **Real job budgets.** Kernel accepts an optional per-run `max_turns` override. When a standing Job phase runs, use the phase's `max_turns` if set, else the agent's. Phase fields become `Optional[int] = None` meaning "inherit the agent's budget" (no hidden 10). Existing phase rows with 10 are treated per Open decision 3.
4. **Handoff envelope 10 / 60s:** the envelope `max_turns` default becomes None (inherit child profile); `timeout_seconds` is either wired to the same time-limit check or removed (decide at build from actual usage).

### Beat 4: What dies today

1. Hard-coded `max_turns=10` defaults on `Phase` / `PhaseSpec` / `HandoffEnvelope` and in `job_phase_orchestrator.py:179`.
2. `phases.max_turns ... DEFAULT 10` for new databases (becomes nullable = inherit).
3. The "stored but ignored" phase budget: either enforced (this card) or deleted - no decorative field left.
4. `HandoffEnvelope.timeout_seconds` if it is confirmed unused and not wired.

---

## 2. Acceptance criteria (EARS)

- **[REQ-462-001]** WHILE a chat reply is running, WHEN its elapsed time exceeds the configured per-reply limit, THE SYSTEM SHALL finish the current step, start no further model or tool step, and end through the graceful ending path with reason `time_limit`.
- **[REQ-462-002]** WHILE a standing Job phase run is in progress, WHEN its elapsed time exceeds the configured job run limit, THE SYSTEM SHALL end it the same way and record the phase as not completed.
- **[REQ-462-003]** WHEN a standing Job phase has a `max_turns` value, THE SYSTEM SHALL use it as that run's turn budget instead of the agent's.
- **[REQ-462-004]** WHEN a phase or handoff has no `max_turns`, THE SYSTEM SHALL use the agent's `max_turns`.
- **[REQ-462-005]** THE SYSTEM SHALL NOT carry a literal default of 10 for phase or handoff budgets.
- **[REQ-462-006]** THE SYSTEM SHALL let the operator view and change both time limits in Settings.

### Tests (write first at build)

1. Kernel with a fake clock: the limit passes after step 2 -> no 3rd step; graceful helper called with `time_limit`.
2. Phase run with `max_turns=3` on an agent at 50 -> stops after 3 passes; phase without a value -> agent's 50.
3. Handoff with no envelope budget -> child profile's budget.
4. Settings API round-trip for both limits.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill.
2. Settings -> set the chat per-reply time limit to **15 seconds**.
3. With the AutoReiv repo as the active project, Chat Studio -> **Developer**: `Read every card in docs/cards one by one and summarize each.`
4. Expected: after about 15 seconds the reply ends with a short summary of what it covered and a "keep going" cue - no error text.
5. Set the limit back to the default.

**Failure signals:** the reply keeps running past the limit; a bare error; a tool cut off mid-write.

---

## 4. Open decisions for Jacob

1. **Chat per-reply time limit:** proposed **10 minutes**, global. (Or per agent?)
2. **Standing Job run time limit:** proposed **30 minutes** per phase run.
3. **Job turn budget:** should standing Jobs just use the agent's budget (simplest), or get their own default (e.g. 100)? And should existing phase rows stored with 10 be treated as "inherit" (proposed) or kept at 10?
4. **Split?** Keep as one card, or split time limit and job budgets.

---

## 5. Constraints

- Docs-only until **build**.
- Do not kill tools mid-execution; checks happen between steps.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 6. Reply phrases

- Lock the numbers: say **continue** with the values.
- Start implementation: say **build**.
- After the runbook passes: say **merge to qa**.
