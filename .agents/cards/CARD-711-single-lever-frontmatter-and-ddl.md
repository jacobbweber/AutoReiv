---
id: CARD-711
title: "Consolidate duplicate YAML frontmatter parsers, SKILL.md path/tool resolvers, and duplicate SQLite DDL table definitions"
type: feature
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-711-single-lever-frontmatter-and-ddl]
  checks: [tests/unit/architecture/test_card711_single_frontmatter_and_ddl.py]
branch: feat/card-711-single-lever-frontmatter-and-ddl
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-711 Consolidate duplicate YAML frontmatter parsers, SKILL.md path/tool resolvers, and duplicate SQLite DDL table definitions

## Intent
Enforce `.agents/rules/code-quality.md` ("One capability, one code path") across markdown frontmatter parsing, `SKILL.md` resolution, and SQLite schema DDL.

## Goal
1. One canonical YAML frontmatter splitter/parser shared across `ContentStore`, `WikiStore`, `SDLC`, and skill tooling instead of 11 separate implementations.
2. `ContentStore` and `allowed_tools.py` are the single resolvers for `SKILL.md` files and tool-to-skill bindings; duplicate resolvers in `UserSkillCatalog`, `workshop.py`, `dynamic_loader.py`, and `ToolSkillResolver` delegate to the canonical path.
3. `src/infrastructure/memory/schema.py` is the single place defining SQLite `CREATE TABLE` DDL (`connection.py` no longer duplicates inline `CREATE TABLE` statements for `prompt_catalog`, `credentials`, `remote_hosts`, and `agent_capability_gaps`).

## Change
- Extract a shared, pure YAML frontmatter parser utility in `src/domain/` and replace the duplicate regex/line-splitting implementations across `content/store.py`, `dynamic_loader.py`, `runbook_frontmatter.py`, `linter.py`, `distillation_service.py`, `wiki_tools.py`, `tool_skill_resolver.py`, `quiz_engine.py`, and `developer_authoring.py`.
- Collapse `UserSkillCatalog`'s three `resolve_*_skill_md` helpers and `_allowed_skill_ids_for_current_agent` onto `ContentStore.skills` and `ticked_skills()` from `src/application/agent_skills/allowed_tools.py`, and move `ToolSkillResolver` out of `src/domain/observability/` to delegate to `ContentStore` / `allowed_tools`.
- Deduplicate inline `CREATE TABLE` DDL in `src/infrastructure/memory/connection.py:205-263` so `schema.py` owns all DDL constants.

## What dies
- 10 duplicate YAML frontmatter splitting helpers across `src/application/` and `src/domain/`.
- Duplicate wildcard skill expansion in `UserSkillCatalog._allowed_skill_ids_for_current_agent` and duplicate `SKILL.md` disk globbing in `ToolSkillResolver` and `workshop.py`.
- Duplicate inline `CREATE TABLE` blocks in `src/infrastructure/memory/connection.py`.

## Proof
- Journey `card-711-single-lever-frontmatter-and-ddl`:
  1. Inspect skills and tools in Capabilities Studio and run a skill-backed turn in Chat on desktop and phone, verifying frontmatter parsing and tool-to-skill resolution work identically through the single lever.
- Checks:
  - `tests/unit/architecture/test_card711_single_frontmatter_and_ddl.py`

## Plan and decisions
- Phase 2 single-lever consolidation.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-711\...`

## Release note
- Consolidated 11 markdown frontmatter parsers, 6 `SKILL.md` resolvers, and duplicate SQLite DDL table definitions onto single canonical code paths [CARD-711].
