---
id: CARD-607
title: "Toolsmith tries tools it is not offered (lookup_agents, list_project_dir, active_project_info)"
status: In Review
created: 2026-10-02
branch: feat/card-607-610-tool-noise
related:
  - CARD-596
  - CARD-599
labels:
  - type:bug
  - area:agents
  - area:kernel
  - P3
needs_decision: none
milestone: M24
---

# [CARD-607] Toolsmith tries tools it is not offered (lookup_agents, list_project_dir, active_project_info)

> **Status**: In Review (2026-10-03)
> **Labels**: `type:bug`, `area:agents`, `area:kernel`, `P3`

## Why

Found in the CARD-599 ts-02 live runs (2026-10-02, :8770, nemotron-3.5-lightning). Toolsmith called `lookup_agents`, `list_project_dir` and `active_project_info`, and each call came back `tool_not_offered`.

These tools exist in the codebase (`orchestration_tools.py`, `project_dev_tools.py`, `project_file_tools.py`), but Toolsmith is not given them. CARD-596 also removed `lookup_agents` from the default platform tools. The calls waste steps, and before CARD-600's clean-up they led to noisy "failed" notes.

## Scope

1. Find where the names reach Toolsmith: the instructions, skill runbooks, tool descriptions, memory facts, or the scaffold/forge text (`forge/scaffold.js`, `forge/tools.js`).
2. Remove or update the stale mentions.
3. Make the `tool_not_offered` result name the nearest offered tool, so the model can recover in one step.

## Out of scope

Changing Toolsmith's tool set. Routing (CARD-596).

## Acceptance criteria

- 5 ts-02 runs on nemotron: no `tool_not_offered` calls.
- A unit test covers the `tool_not_offered` hint.
- Full preflight is green.

## Implementation (2026-10-03, branch feat/card-607-610-tool-noise)

- Cause: `list_available_skills_and_tools` (Toolsmith checks it before building) lists every registered tool, including `lookup_agents`, `list_project_dir`, `active_project_info`; the model read "exists" as "callable". Agent Studio also still advertised `lookup_agents` / `handoff_to_agent` (new-agent scaffold prompt and the OS BASELINE grid) after CARD-596.
- The catalog now marks each tool `you_can_call` (true only for tools sent on this call, from the tool context `offered_tools`); the note says any other call is refused. Toolsmith's instructions say the catalog is for checking only.
- `tool_not_offered_error()` (tool_registry.py), used by both the kernel gate and the registry: keeps the `tool_not_offered:` prefix, adds "Did you mean X?" (difflib) and "Tools you can call now: ..." (up to 25, then "+N more"); with nothing offered, "answer in text".
- A refused call (not offered, bad arguments, not authorized, unknown name) no longer counts as a failed tool for the "Note: ... failed" line (shared `is_self_correcting_refusal`, see CARD-610).
- Agent Studio: the OS BASELINE grid now mirrors `REQUIRED_PLATFORM_TOOLS` (ask_clarification, get_session_info, recall_agent_memory, memorize_fact, read_document_file); the scaffold prompt says "say so plainly, name the agent that covers it if you know one, suggest Ask Developer; call only the tools you are given". app.js v2.0.102.
- Left alone: `platform/skills/coordination` and `native-tool-engineering` still grant `handoff_to_agent` (out of scope: Toolsmith's tool set).
- Tests: `tests/unit/kernel/test_card607_tool_not_offered.py` (7), `tests/unit/frontend/card_607_baseline_and_scaffold.test.js` (2); three vitests updated for the baseline list.

## Results (live, :8770, nemotron-3.5-lightning, 2026-10-03)

| Run | tool_not_offered | Saved tool | Notes |
|---|---|---|---|
| ts-02 #1 count_words | 0 | count_words_1, disabled, check passed | catalog 1 call, register 1 call |
| ts-02 #2 count_vowels | 0 | count_vowels_2, passed | spurious "Not done: Register tool..." line (CARD-599 checker) |
| ts-02 #3 reverse_words | 0 | reverse_words_3, passed | spurious "Not done" lines for empty handoff fields |
| ts-02 #4 celsius_to_fahrenheit | 0 | celsius_to_fahrenheit_4, passed | reply ends "You can use Ask Developer to add this." |
| ts-02 #5 title_case | 0 | title_case_5, passed | spurious "Not done" lines |

Acceptance: 5/5 runs with no `tool_not_offered`. Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003d\agent-studio-baseline-grid-desktop.png`, `...\ui1003d\toolsmith-run-1..5-chat-desktop.png`.
