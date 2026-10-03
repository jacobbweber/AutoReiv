---
id: CARD-599
title: "Multi-step requests: nemotron silently skips steps; the reply must cover every ask or say what was skipped"
status: In Review
created: 2026-10-01
branch: feat/card-599-600-reply-honesty
related:
  - CARD-461
  - CARD-551
labels:
  - type:bug
  - area:kernel
  - area:models
  - P2
needs_decision: none
milestone: M24
---

# [CARD-599] Multi-step requests: nemotron silently skips steps; the reply must cover every ask or say what was skipped

> **Status**: In Review (2026-10-02)
> **Labels**: `type:bug`, `area:kernel`, `area:models`, `P2`

## Why

Battery 2026-09-30, ts-02: the Toolsmith was asked for 6 things (remember, recall, session info, list agents, list skills + runbook, read a file). On nemotron-3.5-lightning it did 3 and did not say it had skipped the rest. qwen3.8 did all 6. (Moved from docs/findings.md.)

## Scope

1. **Reproduce:**
   - Add the ts-02 prompt as a scripted check: a throwaway :8770, 5 runs on nemotron.
   - Count asks done, and skipped asks that were or were not reported.
2. **Fix, cheapest first:**
   - a. A platform rule in the generated instructions: "If the request has several parts, do each one; end by listing any part you did not do and why."
   - b. If (a) is not enough: a short no-tools check after the final reply, on the same model. It compares the user's asks with the tools that ran and appends "Not done: ..." when parts were skipped.
   - No model swaps; extra local calls are acceptable.

## Out of scope

Model changes. Routing.

## Acceptance criteria

- On the ts-02 prompt (5 runs, nemotron), every run either does all 6 parts or names each skipped part in the reply.
- Fast preflight is green.

## Change

Shared branch with CARD-600 (both change the kernel's final-reply path).

- Platform rule block "## Answering" (after "## Your domain"): do every part of a request, or say plainly which part was not done and why; never say an action was done unless a tool did it.
- New `src/agent/reply_rules.py`: `request_parts` splits the request into its asks; a no-tools check on the same model (full reply token budget, so nemotron's thinking does not eat the answer) goes part by part against the tool calls that actually ran and writes "Done:" / "Not done:" lines. Missing parts are appended to the reply as "Not done: ..." lines.
- Runs only in `stream_turn(parts_request=...)`: the chat router's short-turn path passes the user message (not on resume). Needs 3 or more parts and a reply that does not already say something was skipped. `run_turn` (routines, handoff children, phases) never runs it.
- Tests: `tests/unit/kernel/test_card599_skipped_parts.py`.

## Results

| Check | Result | Notes |
|---|---|---|
| Kernel suite | PASS | 213 passed |
| Full pytest | PASS | 2320 passed, 12 skipped |
| Full preflight (`--base origin/qa`) | PASS | ruff, eslint (0 errors, 3 warnings), pytest 2320, vitest 944, smoke 76 |
| Live AutoReiv, 4 asks (remember Bar Harbor, session ID, list templates, search weekly planning) | PASS | Rule only: 1 of 3 skipped "remember" silently, 1 more claimed "noted" with no tool. With check v1: 5/5 OK (3 did all, 2 skipped memorize and got "Not done: Remember ... Bar Harbor"). Check v2: 3/3 did all 4. Screenshot run skipped memorize and got the Not done line. |
| Live Toolsmith ts-02, 6 asks | PASS | v1: 4/5 (one run skipped 2 parts unnamed). v2 (part by part, current): 5/5 named every skipped part. One false positive: "Not done: Recall test token memory" although recall ran. |
| Offline checker probe, 8 recorded replies | PASS | 8/8 correct |

Live env: throwaway :8770 from a temporary merge of the CARD branches (deleted after), Spark nemotron-3.5-lightning only. Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1002c\599-multi-step-reply.png`.

## Found while testing

- Nemotron skips `memorize_fact` in about 30-40% of multi-ask runs.
- AutoReiv can make about 21 wiki search/list calls for one simple search.
- Toolsmith tries tools it is not offered (`lookup_agents`, `list_project_dir`, `active_project_info`).

## Release note

When a Chat request has several parts and the agent skips one, the reply now ends with a "Not done: ..." line naming it instead of skipping it silently.
