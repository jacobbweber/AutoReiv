# [CARD-104] Mount user agentskills.io packs (progressive disclosure) alongside Python builtins

> **Status**: In Review
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/control-plane-data-dir/`
> **Labels**: `type:feature`, `area:skills`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**:
> **github_issue**:

---

## 1. Why / Intent
`DynamicSkillLoader` already parses agentskills.io `SKILL.md` and is unused at bootstrap. Slice B mounts USER packs from `$DATA_DIR/skills` with progressive disclosure. Python Builtin skills stay as they are.

## 2. What to Build
- Scan `$DATA_DIR/skills/**/SKILL.md` after today's `BuiltinAgentRegistry.bootstrap` Python `register_tools` calls.
- Catalog list: frontmatter name + description + path only. Load body and JSON tool blocks on demand via `load_skill_from_markdown`.
- Missing `skills/` dir: Python builtins still register.
- Name collision: builtin tool wins; skip or suffix the user tool; honest log.
- Do not replace Python skill classes with markdown. Do not execute user JSON as Python.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-DATA-009]`: User packs from `$DATA_DIR/skills` are listed at bootstrap via `DynamicSkillLoader`. Today's Python builtins still register when the dir is missing.
- [x] `[REQ-DATA-010]`: List is name+description only. Body and tools load on demand.
- [x] `[REQ-DATA-011]`: Colliding user tool names do not overwrite Python builtins.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check` on touched Python.

## 4. Constraints & Honor Flags
- Do not clone. Do not push. Stay on `qa`.
- Depends on CARD-102 data dir. No kernel changes. No Agent Builder specialist. No SkillOpt. No ACE.
- Existing `GET /api/skills/catalog` (CARD-018) stays. User packs are additional.
- Spec: `docs/specs/control-plane-data-dir/`.

