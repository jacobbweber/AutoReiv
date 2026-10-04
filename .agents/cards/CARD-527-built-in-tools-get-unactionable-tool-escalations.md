---
id: CARD-527
title: "Built-in tools get tool-escalation cards that the Developer cannot act on (get_recent_errors, list_available_skills_and_tools)"
status: In Review
created: 2026-09-26
branch: feat/card-525-527-545-friction-dedup-builtin-native-risk
related:
  - CARD-520
  - CARD-354
  - CARD-525
labels:
  - type:product
  - area:observability
  - area:tools
  - P3
needs_decision: none
milestone: M25
---

# [CARD-527] Tool escalations for built-in tools point at the Developer, who only authors custom tools

> **Status**: In Review (2026-10-04, branch `feat/card-525-527-545-friction-dedup-builtin-native-risk`, not merged). Found in the CARD-520 live-test seed, 2026-09-26.
> **Related**: CARD-520 (Ask Developer on friction cards), CARD-354 (friction auditor), CARD-525 (dedup)
> **Labels**: `type:product`, `area:observability`, `area:tools`, `P3`

## Evidence

- A 24 h audit on Jacob's own data staged two tool escalations for **built-in** tools from real chats: `get_recent_errors` returned 12,599 bytes (skill `packs/autoreiv/skills/platform-health/SKILL.md`) and `list_available_skills_and_tools` returned 20,146 bytes (skill `packs/developer/skills/capability-authoring/SKILL.md`, recorded for agent `autoreiv`).
- Both cards offer **Ask Developer**, which opens a Developer chat with intent `modify`. The Developer's Tools Studio path authors and registers **custom** tools (`application/tools/developer_mediation.py`); built-in tools are Python in this repo (`application/skills/agent_builder_tools.py` and others), so the chat cannot change them. The likely result is a new wrapper tool or a confused reply.
- The skill-to-agent mapping also looks off: a `packs/developer/...` skill path on an `autoreiv` recommendation.

## Change (decide at refinement)

- For a built-in tool, say so on the card ("Built-in tool: needs a code change in AutoReiv") and offer a runbook patch that caps usage (for example "call get_recent_errors with limit 20") instead of Ask Developer, or make these tools pagination-aware in code and add them to the auditor's pagination-aware list.
- Check why the capability-authoring skill path is attached to an `autoreiv` recommendation.

## Done when

A built-in tool never gets an Ask Developer card; it gets either a patch it can apply or a clear "needs a code change" label; `get_recent_errors` and `list_available_skills_and_tools` stay under 8 KB by default or accept a limit.

## Log

- 2026-09-29: battery triage: still valid; the escalation button now opens Toolsmith (CARD-571), which also cannot change a built-in tool

## Built (2026-10-04)
- `ScopedToolRegistry.builtin_tool_names()`: tools with origin `platform` that are not `mcp_`. Runtime-built tools now mount with origin `native_custom`, and MCP mounts with `mcp`. The audit gets the registry from the serve (route) and the kernel (routine).
- Payload bloat on a built-in tool that takes no limit gets a new remedy, `code_change`. The card says "Built-in tool: code change" and "Needs a code change in AutoReiv", and its only button is Dismiss. Apply and Ask Developer answer 409 with a plain sentence. Runtime-built, MCP and unknown tools keep Ask Developer.
- `get_recent_errors` returns the newest errors that fit in 7.5 KB, with messages cut to 300 characters and span metadata only on request (`include_metadata`). `list_available_skills_and_tools` takes `query`, `limit` and `offset`, shortens descriptions and stays under 7.5 KB, with counts and `next_offset`. Both are now pagination-aware, so their friction gets a "specify limit" runbook patch.
- Skill mapping: the agent's own ticked skills are tried first. Cause of the `packs/developer` path on an `autoreiv` card: the resolver took the first skill (alphabetical) whose `tools:` listed the tool, whoever the agent was.
- Applying a patch to a skill that exists only as a shipped copy now writes its user copy (with `based_on`) first. Before, Apply answered "The skill file ... no longer exists" for every shipped-only skill, which is most of them.

## Plan and decisions
- D1: a built-in tool's card is honest and inert (Dismiss only). Jacob cards the code change himself; the app does not file cards.
- D2: unknown tools (in no registry) keep Ask Developer; only tools the registry knows as built-in are excluded.

## Results
| Check | Result | Notes |
|---|---|---|
| Unit: resolver, registry, audit with registry and ticked skills, routes 409, shipped-only Apply, both tools under 8 KB, paging skips nothing | PASS | `tests/unit/observability/test_card527_builtin_tool_friction.py` (14 tests) |
| Vitest: code_change card shows badge, note and Dismiss, no Apply / Ask Developer | PASS | `tests/unit/frontend/card_527_code_change_card.test.js` (3) |
| Live :8770: `system_info` (built-in) | PASS | `code_change`; Apply 409 "This is a built-in AutoReiv tool: it needs a code change..."; escalate 409 |
| Live: `get_recent_errors` | PASS | runbook patch on `platform-health` (autoreiv's ticked skill); Apply 200 and wrote the user copy (`based_on: 5f2e8c27743b6ec5`) with the bullet |
| Live: `c545_weather` (runtime-built), `mcp_demo_dump`, unknown tools | PASS | Ask Developer kept |
| Live catalog size (real :8770 registry, 109 tools, 46 skills) | PASS | old shape >= 31,869 bytes; new default 7,604 bytes (22 tools, 23 skills, next_offset 22); `query=weather` 899 bytes |
| Screenshots | PASS | `autoreiv-qa\ui1003l\527-friction-builtin-code-change-card.png`, `-desktop.png`, `-phone.png` |

The friction sessions were seeded (oversized tool messages written to the :8770 DB), not produced by a model. These checks used the API and UI with no model call (Spark Nemotron returned no token between 12:52 and 1:11 AM ET on 2026-10-04; :8770 was configured for it from the start).

## Findings
- Fixed here: a runbook patch on a shipped-only skill could never be applied (see Built).
- CARD-629 (Ready): on a phone the friction card header squeezes the summary into a narrow column (screenshot `527-friction-builtin-code-change-phone.png`).

## Release note
A friction card for a built-in AutoReiv tool now says it needs a code change instead of offering Ask Developer. `get_recent_errors` and the authoring catalog stay under 8 KB. Applying a runbook patch to a shipped skill works.

Full suite on `9d13b9ae`: pytest 2502 passed / 12 skipped; preflight GREEN (vitest 1052, smoke 83/83).
