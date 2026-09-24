---
id: CARD-461
title: "Graceful ending at the turn limit: final no-tools summary instead of a bare error"
status: Ready
created: 2026-09-24
branch: qa
adr: none
related:
  - CARD-445
  - CARD-460
  - CARD-462
labels:
  - type:feature
  - area:kernel
  - area:chat
  - P1
---

# [CARD-461] Graceful ending at the turn limit: final no-tools summary instead of a bare error

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-445 discussion - when a reply runs out of turns the user only sees `Execution terminated: Max turn budget of N reached.` and loses what the agent had already done.
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:kernel`, `area:chat`, `P1`
> **Related**: [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) (default 50), [CARD-460](./CARD-460-kernel-repeat-guard-reuse-result-before-stop.md) (loop stops reuse this ending), [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md) (time limit reuses this ending)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the card - **still no product code** |
| **`build`** | Implement the graceful ending test-first (sync + stream) |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | Nothing |
| **Unlocks** | [CARD-460](./CARD-460-kernel-repeat-guard-reuse-result-before-stop.md) and [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md) end through the same helper |
| **Blocked by** | Nothing |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. When an agent runs out of steps, it should tell me in normal words what it finished and what is left, instead of a cold error.
2. I can then say "keep going" and it carries on from where it stopped.

### Beat 2: What AutoReiv does now

1. `src/application/kernel/agent_kernel.py` loops `for turn_idx in range(agent.max_turns)` (sync `run_turn` ~L949, stream `stream_turn` ~L1325).
2. When the loop runs out:
   - sync (~L1242-1252): `ReactState.FAILED`, ACE failed flush, saves `ChatMessage(content="Execution terminated: Max turn budget of {agent.max_turns} reached.")` and returns it;
   - stream (~L1741-1757): same, plus a `TURN_END` event with that text.
3. Nothing summarizes the work. Tool results are in history, but the visible reply is only the error line.
4. A follow-up user message already starts a fresh reply with a fresh budget and the full history, so "keep going" works mechanically today, but the user has no cue to say it and no picture of what is left.
5. Standing Job phases run through the same kernel, so a phase that hits the limit also ends with the bare line.
6. `tests/unit/education/test_card444_flashcard_turn_skill_efficiency.py` uses `BUDGET_TERMINATOR_PREFIX = "Execution terminated: Max turn budget of"` to assert the terminator is absent.

### Beat 3: What will change

1. **One helper** in the kernel, e.g. `_finish_gracefully(reason, ...)`, used by the budget stop in both paths (and by CARD-460 loop stops and the CARD-462 time limit).
2. **One final pass with no tools.** When the budget runs out, make exactly one more model call with **no tool schemas** and a short system instruction: you have reached the step limit for this reply; do not call tools; in a few short lines say what you finished, what is left, and that the user can say "keep going". This call does not count toward `max_turns`.
3. **Save that text as the reply** (streamed normally in the stream path), then append a fixed footer so the cue is always present: `(Stopped at the N-step limit for one reply. Say "keep going" to continue.)`.
4. **Fallback** when the final pass fails, times out, or returns empty (or tries to call a tool): save a fixed plain-English message: `I hit the limit of N steps for one reply before finishing. Say "keep going" and I'll pick up where I left off.`
5. **Status stays honest:** the reply is still recorded as not completed (`ReactState.FAILED` with reason `turn_limit`, ACE failed flush) so Jobs, ACE and training never count it as success. A standing Job phase stores the summary as its output but stays incomplete.
6. **"Keep going" needs no special command.** The next user message is a normal reply with a fresh budget and full history. Test that the tool results from the stopped reply are in the history the next reply sees.
7. Update `test_card444...` to use the new footer marker instead of the old prefix.

**Ideas placed elsewhere:** a per-reply time limit and different budgets for chat vs standing Jobs are in [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md) (kept separate so this card stays one change).

### Beat 4: What dies today

1. `f"Execution terminated: Max turn budget of {agent.max_turns} reached."` in both kernel paths.
2. The duplicated sync / stream budget-stop blocks (~L1242-1252 and ~L1741-1757), replaced by the shared helper.
3. `BUDGET_TERMINATOR_PREFIX` in `test_card444_flashcard_turn_skill_efficiency.py` (replaced by the new marker).

---

## 2. Acceptance criteria (EARS)

- **[REQ-461-001]** WHEN a reply reaches `max_turns`, THE SYSTEM SHALL make exactly one additional model call with no tools available, asking for a short summary of what was done and what remains.
- **[REQ-461-002]** WHEN that final call returns text, THE SYSTEM SHALL save and show it as the reply, followed by the footer `(Stopped at the N-step limit for one reply. Say "keep going" to continue.)`.
- **[REQ-461-003]** IF the final call fails, times out, returns empty text, or requests a tool, THEN THE SYSTEM SHALL save the fixed fallback message naming N and "keep going", and SHALL NOT execute any tool.
- **[REQ-461-004]** THE SYSTEM SHALL behave the same in the sync and streaming kernel paths; in streaming, the summary SHALL stream as normal assistant text and end with `TURN_END`.
- **[REQ-461-005]** WHILE a reply ended at the limit, THE SYSTEM SHALL record it as not completed (ReactState FAILED, reason `turn_limit`, ACE failed flush).
- **[REQ-461-006]** WHEN the user sends a new message after a limit stop, THE SYSTEM SHALL start a new reply with a fresh budget and the stopped reply's tool results in history.
- **[REQ-461-007]** THE SYSTEM SHALL NOT save the text `Execution terminated: Max turn budget of`.

### Tests (write first at build)

1. Kernel sync + stream with a mocked gateway that always requests a tool and `max_turns=2`: the gateway is called 3 times; the 3rd call has no tools; the saved reply equals the summary + footer.
2. Final call raises / returns empty / returns a tool call -> fallback text saved, tool executor not called.
3. Status: ReactState FAILED with reason `turn_limit`; ACE failed flush called.
4. Next-turn history contains the tool results from the stopped reply.
5. Grep guard: the old terminator string no longer exists in `src/`.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill.
2. Agent Studio -> **Developer** -> set Max turns to **2** -> Save.
3. With the AutoReiv repo as the active project, Chat Studio -> **Developer**: `List the project root, then read README.md, AGENTS.md and CHANGELOG.md and give me one line about each.`
4. Expected: the reply stops early but is a short normal-language summary (e.g. listed the root and read README; AGENTS and CHANGELOG remain) ending with `(Stopped at the 2-step limit for one reply. Say "keep going" to continue.)`.
5. Send `keep going`. Expected: it continues and reads the remaining files.
6. Set Developer Max turns back to **25** -> Save.

**Failure signals:** `Execution terminated: Max turn budget of 2 reached.`; no footer; "keep going" starts over from scratch.

---

## 4. Constraints

- Docs-only until **build**.
- Exactly one extra model call per limit stop; never loops.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 5. Reply phrases

- Refine the card: say **continue**.
- Start implementation: say **build**.
- After the runbook passes: say **merge to qa**.
