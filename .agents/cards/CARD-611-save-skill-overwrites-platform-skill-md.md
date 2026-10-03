---
id: CARD-611
title: "Saving a skill whose id matches a platform skill overwrites the shipped platform/skills/<id>/SKILL.md, even with a temp skills folder"
type: bug
status: Ready
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/skills/test_card611_save_skill_never_writes_platform.py]
branch: feat/card-611-save-skill-platform-guard
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-570
  - CARD-610
  - CARD-427
---

# CARD-611 Saving a skill whose id matches a platform skill overwrites the shipped platform/skills/<id>/SKILL.md, even with a temp skills folder

## Problem
While writing the CARD-610 tests (2026-10-03), `UserSkillCatalog(skills_dir=<tmp>/skills).save_skill("wiki", "wiki", "Wiki SOP.", ...)` rewrote the repo's `platform/skills/wiki/SKILL.md` (59 lines replaced by a 3-line stub). The catalog was pointed at a temp folder, yet the write landed in the shipped platform pack. It was caught in `git status` and reverted; the CARD-610 test now uses a non-platform id. Anything that saves a skill by a platform id (a test, an accepted online-ACE `propose_skill`, Skill Studio) can silently overwrite a shipped runbook in the checkout.

## Cause
`save_skill` in `src/application/skills/user_catalog.py`: when `resolve_skill_md(skill_id)` (inside `skills_dir`) does not exist yet, it falls back to `resolve_skill_scoped_skill_md(skill_id)`, which asks the global content store (`get_store().skills.load`) for the winning SKILL.md, and for a platform id that is the repo copy under `platform/skills/` (CARD-570). The write then goes to that path. The fallback ignores the catalog's own `skills_dir`.

## Change
- `save_skill` writes only inside the catalog's `skills_dir` (the data copy). Saving a platform id creates or updates the data-dir override (`$DATA_DIR/skills/<id>/SKILL.md`), which already wins over the platform copy at load time; it never writes under `platform/`.
- Check the other write paths that resolve through the store (ACE sidecar append, `commit` / apply of an accepted `propose_skill`, snapshot/rollback in `ace_online.py`) for the same fallback.
- A unit-test guard: with a temp `skills_dir`, saving `wiki` leaves `platform/skills/wiki/SKILL.md` byte-identical and creates `<tmp>/skills/wiki/SKILL.md`.

## What dies
Writes into `platform/skills/` from any runtime save path.

## Proof
- Check: `tests/unit/skills/test_card611_save_skill_never_writes_platform.py` (platform file bytes and mtime unchanged; data copy created; the data copy wins on the next load).
- Negative: saving a non-platform id still creates it in `skills_dir`.

## Plan and decisions
- Overrides belong in the data dir; the repo copy is read-only at runtime (CARD-427 already says skill runbooks are not copied into `$DATA_DIR/skills/` for chat reads, which is unaffected).

## Findings
- (from the CARD-610 build, 2026-10-03)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Saving a skill that shares a name with a built-in skill no longer overwrites the built-in runbook; your copy is saved in your data folder.
