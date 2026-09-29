---
id: CARD-578
title: "Tools load all at once"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: feat/card-578-tools-load-all-at-once
related:
  - CARD-562
  - CARD-566
  - CARD-577
  - CARD-539
  - CARD-454
labels:
  - type:feat
  - area:kernel
  - P1
needs_decision: none
milestone: M24
---

# [CARD-578] Tools load all at once

> **Status**: Done
> **Labels**: `type:feat`, `area:kernel`, `P1`

## Why

Jacob, 2026-09-29: keep AutoReiv on course; tools load all at once. The 15-tool per-turn cap pinned 10 project/card
tools and ranked the rest, so Developer (allowed 26) never saw `skill_view` on a plain turn and lost `ask_clarification`
on a coding turn (CARD-577 probe). `activate_skill` only reordered tools inside the cap. A tool left off the list still
ran if the model named it, and a bare name could run an `mcp_*` tool by suffix match.

## Change ([ADR-0064](../../docs/adr/0064-tools-load-all-at-once.md), supersedes the ADR-0054 cap)

- **All at once:** `_resolve_active_tools` returns every allowed tool (ticked-skill tools + base tools). Deleted
  `MAX_ACTIVE_TOOLS_PER_TURN`, `PROJECT_CORE_TOOLS`, `CARD_WORK_TOOLS`, `BASELINE_COORDINATION_TOOLS`, the ranking and
  filler-word logic, `_match_intent_skills`, `_get_discovered_mcp_domains`, `_capability_authoring_requested`, the
  per-turn active-skills state, `ticked_skills_for_domains` / `DOMAIN_EXTRA_TOOLS` and the unused `tool_ranker.py`.
- **Policy still narrows (kept on purpose):** Direct gets none; a Formulate phase gets no work tools (CARD-554); a job
  phase locked to matched capabilities gets those plus the required platform tools; education priming drops the
  forbidden wiki tools. These mirror what ToolPolicyGate enforces; a normal chat turn has none of them.
- **`activate_skill` removed** (platform primitive, REQUIRED_PLATFORM_TOOLS, gate safe list, Agent Studio baseline chips,
  AutoReiv prompt wording). Every agent's count drops by one. `skill_view` / `list_user_skills` are always sent when the
  agent has ticked skills.
- **Only a sent tool runs:** both ReAct loops pass the names sent on that call to `_gate_tool_call` and the registry;
  anything else is refused with `tool_not_offered` before policy or approval. A HITL resume (not a model call) checks the
  allowed set only.
- **Exact names:** the bare-name suffix match to `mcp_*` tools is gone from `_execute_inner` (wildcard skill bindings stay).
- Linter CAP-001 (15 per skill) stays as an authoring guideline; the tool-bloat detector is advisory at 50.
- Docs: ADR-0064; notes on ADR-0052/0054/0061; the Developer 26-vs-15 finding removed.
- Tests: new guard `tests/unit/kernel/test_card578_tools_all_at_once.py`; cap/ranking/activation tests deleted or rewritten
  (test_resolve_active_tools, test_card562_project_core_tools, test_dynamic_skill_scoping, test_tool_ranker deleted).

## Acceptance

- [x] Every tool from the agent's ticked skills plus the base tools is sent on every call (guard test, all 5 tool agents).
- [x] No cap, ranking, pinning or keyword matching remains; `tool_ranker.py` deleted.
- [x] `activate_skill` removed; `skill_view` / `list_user_skills` sent whenever the agent has skills.
- [x] A tool not sent on that call is refused (gate and registry); bare `mcp_*` suffix names are refused.
- [x] ADR-0064, findings, tests updated; no "activate skill" wording left in skills or prompts.
- [x] Live test on :8770 (below).

## Log

- 2026-09-29: implemented on the branch; ruff, pytest (2006 passed), vitest (957), preflight --fast --base qa GREEN.
- 2026-09-29 live test, throwaway :8770, Nimo qwen3.8:latest ctx 262144, turn spans from the QA DB:

  | Agent | Tools sent | Schema chars | Schema tokens | Prompt tokens |
  |---|---:|---:|---:|---:|
  | Developer | 25 | 11,637 | 2,778 | 3,752 |
  | AutoReiv | 38 | 21,475 | 5,169 | 6,500 |
  | Tutor | 32 | 20,186 | 4,878 | 6,282 |
  | Architect | 19 | 9,051 | 2,163 | 3,036 |
  | Toolsmith | 13 | 8,270 | 1,999 | 2,485 |
  | Direct | 0 | 0 | 0 | 10 |

  Developer turn 1 got all 25 tools on every step and, in a throwaway git project, called read_project_file then
  patch_project_file ("Helo" -> "Hello", 1 replacement) and replied in 23.5 s. AutoReiv on "hi" got all 38 tools (the
  wiki tools included) and replied in 25.6 s; asked to search the wiki it called wiki_note_search / wiki_note_list
  directly with no activation step. Architect, Tutor, Toolsmith and Direct "hi" turns all succeeded. Status In Review.
- 2026-09-29: Jacob: merge to qa. Done; merged into qa.
