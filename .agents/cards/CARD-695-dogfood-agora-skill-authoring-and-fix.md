---
id: CARD-695
title: "Dogfood Agora skill authoring and fix post-registration reply and resolver overhead"
type: bug
status: In Review
priority: P1
milestone: M29
needs_decision: none
proof:
  journeys: [card-695-dogfood-agora-skill-authoring-and-fix]
  checks: [tests/unit/kernel/test_card539_selection_narrows.py, tests/unit/kernel/test_card695_post_registration_reply.py]
branch: feat/card-695-dogfood-agora-skill-authoring-and-fix
log: {minutes: 30, qa_runs: 1, findings: 2}
created: 2026-10-16
---

# CARD-695 Dogfood Agora skill authoring and fix post-registration reply and resolver overhead

## Problem
1. During real-world Agora skill dogfooding, an agent reply can end with `"Reply failed: The model returned an empty reply"` right after registering/writing a tool via `write_skill_file` (`docs/findings.md` M25).
2. Every `resolve_allowed_tools` / `ToolPolicyGate` call executes `DataDirResolver().resolve()` and re-parses YAML/AST skill files (~21 s in `test_card539_selection_narrows.py` across 2,400+ calls, and hit on every runtime tool-policy check).
3. The full Agora skill loop (`AutoReiv` authoring 2–3 real user Agora skill folders with `SKILL.md` + `references/` + `tools/*.py`, risk-tiered approval, `skill_view` on-demand tool mounting, and execution in Chat + `#view-capabilities` inspection) needs end-to-end live dogfooding and hardening.

## Cause
- `src/application/kernel/agent_kernel.py` treats an empty final assistant content string after a successful tool-registration/skill-write round as an unrecoverable empty reply instead of synthesizing a concise completion summary from the tool result when the model stops with empty text after a tool call.
- `src/infrastructure/data/resolver.py` (`DataDirResolver.resolve()`) queries SQLite settings on every invocation without caching by `(db_path, mtime, size, wal_mtime, wal_size)` and `_peek_setting_backup_dir()` fell back to `platform_default()` even when `AUTOREIV_DATA_DIR` was set; `src/infrastructure/content/store.py` and `src/application/skills/agora_loader.py` re-parsed unchanged `SKILL.md` YAML and `tools/*.py` AST on every `resolve_allowed_tools` call.
- `ScopedToolRegistry` defined `__len__` without `__bool__`, causing `tool_registry or ...` in `AgentBuilderTools.__init__` to discard an empty `ScopedToolRegistry` instance as falsy.

## Change
- Cache `_read_sqlite_setting()` by `(db_path, st_mtime_ns, st_size, wal_mtime_ns, wal_size, key)` and isolate `_peek_setting_backup_dir()` to the active data root in `src/infrastructure/data/resolver.py`; cache `split_frontmatter` in `src/infrastructure/content/store.py` and `_extract_agora_tool_spec_cached` in `src/application/skills/agora_loader.py`; promote `tests/unit/kernel/test_card539_selection_narrows.py` from `slow` to `guard`.
- Harden `src/application/kernel/agent_kernel.py` (`post_tool_empty_fallback` and `latest_user_prompt` in `src/application/kernel/empty_reply.py`) so a turn that executed one or more tool calls (such as `write_skill_file`) and receives an empty post-tool model message synthesizes a clean completion summary instead of failing with `"Reply failed: The model returned an empty reply"`.
- Fix `ScopedToolRegistry.__bool__` in `src/application/kernel/tool_registry.py` and `AgentBuilderTools` registry binding in `src/application/skills/agent_builder_tools.py`.
- Dogfood the app in live QA (`card-695-dogfood-agora-skill-authoring-and-fix`) by having `AutoReiv` author real user Agora skill folders (`SKILL.md`, `references/*.md`, `tools/*.py`), mount them via `skill_view`, execute their tools in Chat, and inspect them in `#view-capabilities`.

## What dies
- Repeated uncached SQLite connections inside `DataDirResolver().resolve()` and repeated YAML/AST re-parsing on every `resolve_allowed_tools` call.
- Inline `user_req_text` history scan loops in `AgentKernel.run_turn` and `AgentKernel.stream_turn` (consolidated into `latest_user_prompt` in `empty_reply.py`).
- The two corresponding findings in `docs/findings.md` (`test_card539_selection_narrows.py` slow resolver and `"Reply failed: The model returned an empty reply"` after tool registration).

## Proof
- Journey `card-695-dogfood-agora-skill-authoring-and-fix`:
  1. In Chat, ask `AutoReiv` to create two real user Agora skill folders (`SKILL.md`, `references/`, `tools/*.py` — one pure `read_only` auto-enabled tool and one outside-access tool requiring approval) and verify no `"Reply failed: The model returned an empty reply"` occurs.
  2. Open `#view-capabilities`, verify both user skill folders appear in the tree with their inferred schemas and safety statuses, and run the newly authored tools in Chat after `skill_view`.
- Checks:
  - `tests/unit/kernel/test_card539_selection_narrows.py` (promoted to `guard`, verifying fast execution < 3s)
  - `tests/unit/kernel/test_card695_post_registration_reply.py`

## Plan and decisions
- Technical only (`needs_decision: none`).

## Findings
- (fixed) `ScopedToolRegistry` defined `__len__` without `__bool__`, making an initially empty `ScopedToolRegistry` evaluate to `False` in `AgentBuilderTools.__init__` (`tool_registry or ScopedToolRegistry()`) and causing `write_skill_file` to mount tools onto a detached registry. Fixed by adding `ScopedToolRegistry.__bool__` and binding `self.tool_registry` in `AgentBuilderTools.register_tools`.
- (fixed) `DataDirResolver._peek_setting_backup_dir()` queried `self.platform_default() / "database" / "autoreiv.db"` even when `AUTOREIV_DATA_DIR` was set, unlike `_peek_setting_wiki_path()`. Consolidated both onto `_active_setting_db_candidates()`.
- (to findings list) none.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-695-dogfood-agora-skill-authoring-and-fix` | desktop | PASS | AutoReiv authored `dogfood-unit-math` (`SKILL.md`, `references/formulas.md`, `tools/f_to_c.py` auto-enabled) and `dogfood-net-probe` (`SKILL.md`, `tools/probe_url.py` saved disabled for network approval) in Chat with no empty-reply error; verified both in `#view-capabilities`, enabled `probe_url`, and executed `f_to_c(fahrenheit=212) -> 100C` in Chat after `skill_view`. |
| `card-695-dogfood-agora-skill-authoring-and-fix` | phone | PASS | All 5 steps passed on phone viewport (`390x844`). |

Screenshots:
- `/tmp/autoreiv-qa/card-695/card-695-dogfood-agora-skill-authoring-and-fix-desktop-01-in-chat-autoreiv-authors-agora-skill-folder-dogf.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-695\card-695-dogfood-agora-skill-authoring-and-fix-desktop-01-in-chat-autoreiv-authors-agora-skill-folder-dogf.png`)
- `/tmp/autoreiv-qa/card-695/card-695-dogfood-agora-skill-authoring-and-fix-desktop-03-inspect-both-agora-skill-folders-in-view-capabil.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-695\card-695-dogfood-agora-skill-authoring-and-fix-desktop-03-inspect-both-agora-skill-folders-in-view-capabil.png`)
- `/tmp/autoreiv-qa/card-695/card-695-dogfood-agora-skill-authoring-and-fix-phone-03-inspect-both-agora-skill-folders-in-view-capabil.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-695\card-695-dogfood-agora-skill-authoring-and-fix-phone-03-inspect-both-agora-skill-folders-in-view-capabil.png`)

## Release note
- Dogfooded Agora skill authoring end-to-end, eliminated repeated SQLite lookups in `DataDirResolver.resolve()`, and prevented empty-reply failures after tool/skill registration [CARD-695].
