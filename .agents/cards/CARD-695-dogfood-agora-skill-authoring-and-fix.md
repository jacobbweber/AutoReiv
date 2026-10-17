---
id: CARD-695
title: "Dogfood Agora skill authoring and fix post-registration reply and resolver overhead"
type: bug
status: Ready
priority: P1
milestone: M29
needs_decision: none
proof:
  journeys: [card-695-dogfood-agora-skill-authoring-and-fix]
  checks: [tests/unit/architecture/test_card539_selection_narrows.py, tests/unit/kernel/test_card695_post_registration_reply.py]
branch: feat/card-695-dogfood-agora-skill-authoring-and-fix
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-16
---

# CARD-695 Dogfood Agora skill authoring and fix post-registration reply and resolver overhead

## Problem
1. During real-world Agora skill dogfooding, an agent reply can end with `"Reply failed: The model returned an empty reply"` right after registering/writing a tool via `write_skill_file` (`docs/findings.md` M25).
2. Every `resolve_allowed_tools` / `ToolPolicyGate` call executes `DataDirResolver().resolve()`, opening the live SQLite DB twice to peek settings (~5 ms per call, ~21 s in `test_card539_selection_narrows.py` across 2,400 calls, and hit on every runtime tool-policy check).
3. The full Agora skill loop (`AutoReiv` authoring 2–3 real user Agora skill folders with `SKILL.md` + `references/` + `tools/*.py`, risk-tiered approval, `skill_view` on-demand tool mounting, and execution in Chat + `#view-capabilities` inspection) needs end-to-end live dogfooding and hardening.

## Cause
- `src/application/kernel/agent_kernel.py` treats an empty final assistant content string after a successful tool-registration/skill-write round as an unrecoverable empty reply instead of synthesizing a concise completion summary from the tool result when the model stops with empty text after a tool call.
- `src/infrastructure/data/resolver.py` (`DataDirResolver.resolve()`) queries SQLite settings on every invocation without caching by `(env_signature, db_mtime)` or passing the resolved root.

## Change
- Cache or short-circuit `DataDirResolver.resolve()` in `src/infrastructure/data/resolver.py` so repeated `resolve_allowed_tools` / `ToolPolicyGate` calls within the same environment and unchanged DB do not re-open SQLite twice per call.
- Harden `src/application/kernel/agent_kernel.py` so a turn that executed one or more tool calls (such as `write_skill_file`) and receives an empty post-tool model message either prompts/synthesizes a clean completion summary instead of failing with `"Reply failed: The model returned an empty reply"`.
- Dogfood the app in live QA (`card-695-dogfood-agora-skill-authoring-and-fix`) by having `AutoReiv` author real user Agora skill folders (`SKILL.md`, `references/*.md`, `tools/*.py`), mount them via `skill_view`, execute their tools in Chat, and inspect them in `#view-capabilities`.

## What dies
- Repeated uncached SQLite connections inside `DataDirResolver().resolve()` on every `resolve_allowed_tools` call.
- The two corresponding findings in `docs/findings.md` (`test_card539_selection_narrows.py` slow resolver and `"Reply failed: The model returned an empty reply"` after tool registration).

## Proof
- Journey `card-695-dogfood-agora-skill-authoring-and-fix`:
  1. In Chat, ask `AutoReiv` to create two real user Agora skill folders (`SKILL.md`, `references/`, `tools/*.py` — one pure `read_only` auto-enabled tool and one outside-access tool requiring approval) and verify no `"Reply failed: The model returned an empty reply"` occurs.
  2. Open `#view-capabilities`, verify both user skill folders appear in the tree with their inferred schemas and safety statuses, and run the newly authored tools in Chat after `skill_view`.
- Checks:
  - `tests/unit/architecture/test_card539_selection_narrows.py` (verifying fast execution < 3s)
  - `tests/unit/kernel/test_card695_post_registration_reply.py`

## Plan and decisions
- Technical only (`needs_decision: none`).

## Findings
- (fixed) ...
- (to findings list) ...

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-695\...`

## Release note
- Dogfooded Agora skill authoring end-to-end, eliminated repeated SQLite lookups in `DataDirResolver.resolve()`, and prevented empty-reply failures after tool/skill registration [CARD-695].
