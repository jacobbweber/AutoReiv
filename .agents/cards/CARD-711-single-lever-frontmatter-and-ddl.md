---
id: CARD-711
title: "Consolidate duplicate YAML frontmatter parsers, SKILL.md path/tool resolvers, and duplicate SQLite DDL table definitions"
type: feature
status: In Review
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-711-single-lever-frontmatter-and-ddl]
  checks: [tests/unit/architecture/test_card711_single_frontmatter_and_ddl.py]
branch: feat/card-711-single-lever-frontmatter-and-ddl
log: {minutes: 15, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-711 Consolidate duplicate YAML frontmatter parsers, SKILL.md path/tool resolvers, and duplicate SQLite DDL table definitions

## Intent
Enforce `.agents/rules/code-quality.md` ("One capability, one code path") across markdown frontmatter parsing, `SKILL.md` resolution, and SQLite schema DDL.

## Goal
1. One canonical YAML frontmatter splitter/parser (`src/domain/frontmatter.py`) shared across `ContentStore`, `DynamicSkillLoader`, `runbook_frontmatter`, `SkillContractCompiler`, `fleet_coordinator`, `distillation_service`, and `ToolSkillResolver`.
2. `UserSkillCatalog._allowed_skill_ids_for_current_agent` delegates wildcard skill expansion to `ticked_skills()` in `src/application/agent_skills/allowed_tools.py`, and `workshop.extract_tools` delegates to `frontmatter_view()`.
3. `src/infrastructure/memory/schema.py` is the single place defining SQLite `CREATE TABLE` DDL (`connection.py` no longer duplicates inline `CREATE TABLE` statements for `prompt_catalog`, `credentials`, `remote_hosts`, and `agent_capability_gaps`).

## Change
- Created `src/domain/frontmatter.py` providing `split_frontmatter`, `split_frontmatter_with_error`, and `join_frontmatter` with LRU caching and CRLF normalization.
- Updated `src/infrastructure/content/store.py`, `src/application/skills/dynamic_loader.py`, `src/application/skills/runbook_frontmatter.py`, `src/application/skills/linter.py`, `src/application/orchestration/fleet_coordinator.py`, `src/application/skills/distillation_service.py`, and `src/domain/observability/tool_skill_resolver.py` to delegate YAML frontmatter splitting to `src.domain.frontmatter`.
- Consolidated wildcard expansion in `UserSkillCatalog._allowed_skill_ids_for_current_agent` onto `ticked_skills()` and `workshop.extract_tools` onto `frontmatter_view()`.
- Extracted `AGENT_CAPABILITY_GAPS_SQL`, `PROMPT_CATALOG_SQL`, `CREDENTIALS_SQL`, and `REMOTE_HOSTS_SQL` in `src/infrastructure/memory/schema.py` and replaced inline `CREATE TABLE` blocks in `src/infrastructure/memory/connection.py` with `conn.executescript(...)`.

## What dies
- Duplicate YAML frontmatter regex/splitting implementations in `content/store.py`, `dynamic_loader.py`, `runbook_frontmatter.py`, `linter.py`, `fleet_coordinator.py`, and `tool_skill_resolver.py`.
- Duplicate wildcard skill expansion branch in `UserSkillCatalog._allowed_skill_ids_for_current_agent` and duplicate frontmatter splitting in `workshop.extract_tools`.
- Duplicate inline `CREATE TABLE` blocks in `src/infrastructure/memory/connection.py`.

## Proof
- Journey `card-711-single-lever-frontmatter-and-ddl`:
  1. Verify `/api/skills/user-skills` returns parsed `SKILL.md` frontmatter cleanly on desktop and phone.
  2. Open Capabilities Studio (`#view-capabilities`) and verify `#capabilitiesTreeList` renders.
- Checks:
  - `tests/unit/architecture/test_card711_single_frontmatter_and_ddl.py`

## Plan and decisions
- Phase 2 single-lever consolidation.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-711-single-lever-frontmatter-and-ddl` | desktop | PASS | Verified `/api/skills/user-skills` returned 14 skills and `#view-capabilities` tree rendered |
| `card-711-single-lever-frontmatter-and-ddl` | phone | PASS | Verified `/api/skills/user-skills` returned 14 skills and `#view-capabilities` tree rendered |

Screenshots:
- `/tmp/autoreiv-qa/card-711/card-711-single-lever-frontmatter-and-ddl-desktop-01-1-verify-skill-catalog-api-returns-parsed-skills-c.png`
- `/tmp/autoreiv-qa/card-711/card-711-single-lever-frontmatter-and-ddl-desktop-02-2-open-capabilities-studio-view-capabilities-and-v.png`
- `/tmp/autoreiv-qa/card-711/card-711-single-lever-frontmatter-and-ddl-phone-02-2-open-capabilities-studio-view-capabilities-and-v.png`

## Release note
- Consolidated markdown YAML frontmatter parsers onto `src/domain/frontmatter.py`, unified wildcard skill and tool extraction onto canonical helpers, and deduplicated inline SQLite `CREATE TABLE` DDL in `connection.py` onto `schema.py` constants [CARD-711].
