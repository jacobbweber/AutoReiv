---
id: CARD-460
title: "Kernel repeat guard: hand back the earlier result before stopping a loop"
status: Ready
created: 2026-09-24
branch: qa
adr: ADR-0043 (amends the cycle-detection behaviour it documents)
related:
  - CARD-445
  - CARD-461
  - CARD-462
labels:
  - type:feature
  - area:kernel
  - area:agents
  - P1
---

# [CARD-460] Kernel repeat guard: hand back the earlier result before stopping a loop

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-445 discussion - with the default turn budget going from 10 to 50, loops must be caught early so the bigger budget is not burned on repeats.
> **ADR Reference**: ADR-0043 (resilience / cycle detection) - this card changes what happens on a hit, not the detector's existence.
> **Labels**: `type:feature`, `area:kernel`, `area:agents`, `P1`
> **Related**: [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) (default 50), [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md) (graceful ending path used when a loop is stopped), [CARD-462](./CARD-462-per-reply-time-limit-and-chat-vs-job-budgets.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine the card (e.g. the open decisions below) - **still no product code** |
| **`build`** | Implement the repeat guard changes test-first |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

Do not write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-461](./CARD-461-graceful-ending-at-turn-limit.md) for the "stop with a summary" path. If this card is built first, it uses a plain-English stop message and switches to CARD-461's helper when that lands. |
| **Related** | [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) - the turn limit (50) stays the backstop |
| **Blocked by** | Nothing |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. If an agent calls the same tool with the same arguments again, it should not run the tool again. Tell it "already done, here is the result" so it can move on.
2. If it keeps repeating anyway (about 3 in a row), stop the reply, but end politely (say what was done), not with a cryptic error.
3. The turn limit stays as the last safety net, not the main loop catcher.

### Beat 2: What AutoReiv does now

**A repeat guard already exists.** `src/application/kernel/cycle_detector.py` `CycleDetector(max_repeats=3, max_churn_repeats=5)`:

1. `record_and_check(tool_calls)` hashes each batch (`tool name + sorted JSON args`) and returns True when:
   - **Identical repeat:** the same batch signature appears 3 times in a row;
   - **Oscillation:** a period-2 or period-3 pattern repeats 3 times (A,B,A,B,A,B);
   - **Churn:** the same tool-name tuple appears 5 batches in a row, **even with different arguments**.
2. `record_and_check_text(text)` catches repeated phrases / n-grams in model text.
3. Wiring in `src/application/kernel/agent_kernel.py`: detector created per reply (sync ~L936, stream ~L1317); text check (~L1079 / ~L1483); tool check before tools run (~L1125 / ~L1535).
4. On a hit the reply hard-stops: `ReactState.FAILED`, an ACE failed flush, and a single saved message `Execution terminated: Detected repetitive cycle calling tools.` (or `...repetitive text generation loop.`). No summary.
5. The **second** identical call is executed again (the tool really runs twice). Only the third is blocked.
6. The churn rule can kill legitimate sequential work such as reading 5 different files in a row with `read_project_file`. That becomes much more likely once the budget is 50.
7. Tests: `tests/unit/kernel/test_streaming_cycle_detector.py`, `tests/unit/gateway/test_resilience.py`.

### Beat 3: What will change

1. **Reuse instead of re-run.** Keep a per-reply record of each executed tool call's signature (tool name + sorted JSON args) and its result. When the model asks for a call whose signature matches a call executed in the **immediately previous** step, do not execute it. Return a tool result instead:
   `Already done: you called <tool> with these exact arguments in the previous step. Here is that result again: <result>. Use it or try a different approach.`
   This counts as a turn (the budget still moves) but the tool does not run twice (no double side effects, no second approval prompt).
2. **Stop on the third identical call in a row** (the model ignored the reuse notice). Stop through CARD-461's graceful ending with reason "repeating the same step", so the user gets a short done / not-done summary.
3. **Oscillation stays** (identical-argument A,B,A,B,A,B is a real loop) and also ends through the graceful path.
4. **Churn rule removed** as a hard stop. Same tool with *different* arguments is normal work; the turn limit (CARD-445, 50) is the backstop.
5. **Text loop** check stays, and ends through the graceful path with plain-English wording.
6. **Exempt tools that are meant to be polled** (e.g. job / status checks where the same call legitimately returns new data). Mechanism: a `repeat_safe` (name at build) flag in tool metadata; exempt tools always execute and never trigger the reuse notice. The initial list is decided at build from the tool catalog (see open decision).
7. Same behaviour in the sync (`run_turn`) and stream (`stream_turn`) paths via one shared helper - no duplicated logic.

### Beat 4: What dies today

1. The churn rule: `max_churn_repeats`, `_tool_name_history` and branch 3 of `CycleDetector.record_and_check`.
2. Re-executing an identical tool call on the very next step.
3. The strings `Execution terminated: Detected repetitive cycle calling tools.` and `Execution terminated: Detected repetitive text generation loop.` in both kernel paths.
4. The duplicated sync / stream cycle-stop blocks in `agent_kernel.py` (replaced by one helper).

---

## 2. Acceptance criteria (EARS)

- **[REQ-460-001]** WHEN the model requests a tool call whose tool name and arguments match a call executed in the immediately previous step, THE SYSTEM SHALL NOT execute the tool and SHALL return the earlier result with an "already done" notice as the tool result.
- **[REQ-460-002]** WHEN the same tool name and arguments are requested 3 steps in a row, THE SYSTEM SHALL stop the reply through the graceful ending path (CARD-461) with reason "repeating the same step".
- **[REQ-460-003]** WHEN the same tool is called in consecutive steps with different arguments, THE SYSTEM SHALL execute each call and SHALL NOT stop the reply for that reason alone.
- **[REQ-460-004]** WHEN an identical-argument oscillation (period 2 or 3) repeats 3 times, THE SYSTEM SHALL stop through the graceful ending path.
- **[REQ-460-005]** WHERE a tool is marked repeat-safe, THE SYSTEM SHALL execute every call to it and SHALL NOT apply the reuse notice or repeat stop.
- **[REQ-460-006]** THE SYSTEM SHALL apply the same repeat guard in both the sync and streaming kernel paths.
- **[REQ-460-007]** WHILE a reply is stopped by the repeat guard, THE SYSTEM SHALL still record it as not completed (ReactState FAILED / ACE failed flush) so jobs and learning do not count it as success.

### Tests (write first at build)

1. Detector unit: identical call on step 2 -> reuse decision; step 3 -> stop decision; different args 6 times -> no stop.
2. Kernel (sync and stream, mocked gateway): the tool executor is called once for two identical consecutive calls; the second tool message contains "Already done" and the first result.
3. Kernel: three identical calls -> reply ends through the graceful helper (asserts the helper was called with the repeat reason).
4. Repeat-safe tool: called 3 times identically -> executed 3 times, no stop.
5. Update `test_streaming_cycle_detector.py` / `test_resilience.py` expectations that relied on churn stops or the old strings.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill.
2. Make sure the AutoReiv repo is the active project in Projects Studio. Chat Studio -> agent **Developer**. Send: `Use read_project_file on README.md. Then call read_project_file on README.md again with exactly the same arguments. Then once more.`
3. Open **+ Options -> Debug** (or Journey). Expected: one real `read_project_file`; the second shows the "Already done" tool result; if the model tries a third time the reply ends with a short plain-English summary, not `Execution terminated: ...`.
4. Send: `Read these five files one after another: README.md, AGENTS.md, CHANGELOG.md, pyproject.toml, package.json. Then list their first lines.` Expected: all five reads run and the reply finishes (no loop stop).

**Failure signals:** the same read executes twice; the five-file request is cut off as a loop; any `Execution terminated: Detected repetitive...` text.

---

## 4. Open decisions for Jacob

1. **Reuse window:** only the immediately previous step (proposed), or anywhere earlier in the same reply?
2. **Repeat-safe list:** proposed start = job / status polling tools and time / clock tools. Confirm, or name others.

---

## 5. Constraints

- Docs-only until **build**.
- Do not raise or remove the turn limit here (CARD-445 owns the number).
- Amend ADR-0043's consequences section at build if behaviour on a hit changes as described.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 6. Reply phrases

- Refine the card: say **continue**.
- Start implementation: say **build**.
- After the runbook passes: say **merge to qa**.
