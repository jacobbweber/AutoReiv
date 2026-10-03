---
id: CARD-611
title: "Saving a skill whose id matches a platform skill overwrites the shipped platform/skills/<id>/SKILL.md, even with a temp skills folder"
type: bug
status: In Review
priority: P1
milestone: M25
needs_decision: none
proof:
  journeys: []
  checks: [tests/unit/skills/test_card611_save_skill_never_writes_platform.py]
branch: feat/card-611-save-skill-platform-guard
log: {minutes: 75, qa_runs: 1, findings: 3}
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

Built (2026-10-03, `feat/card-611-save-skill-platform-guard`):
- `UserSkillCatalog.save_skill` always writes `skills_dir/<id>/SKILL.md` (the jailed data copy). The live copy (data copy, else the shipped one) is read only to keep its other frontmatter; name, description and body are replaced. When the content store's user folder is the same folder, the write goes through `store.skills.save` (records `based_on` for a shipped id, like Skill Studio's workshop save); otherwise it writes the file directly.
- Also fixed on the way: `save_skill` used to write only `name` and `description`, so saving a skill dropped its `tools:` list (and with the old fallback the shipped runbook lost its grants). Tools, tier, version and safety are now kept.
- Unused `render_skill_md` removed.
- Checked the other write paths: `snapshot_skill`, `rollback_skill`, `append_playbook_note`, `record_skill_use` and the curator's archive/unarchive/delete all go through `skill_dir()` (jailed to the data folder); `ContentStore.save`, the workshop save and distillation write the user copy only. No other path writes under `platform/`.
- Undo for a shipped id: the snapshot taken before an accepted self-learning save has no SKILL.md, so rollback removes the data copy and the shipped skill is live again.

## What dies
Writes into `platform/skills/` from any runtime save path.

## Proof
- Check: `tests/unit/skills/test_card611_save_skill_never_writes_platform.py` (platform file bytes and mtime unchanged; data copy created; the data copy wins on the next load).
- Negative: saving a non-platform id still creates it in `skills_dir`.

## Plan and decisions
- Overrides belong in the data dir; the repo copy is read-only at runtime (CARD-427 already says skill runbooks are not copied into `$DATA_DIR/skills/` for chat reads, which is unaffected).

## Findings
- (from the CARD-610 build, 2026-10-03)
- In practice the old bug was reachable from `PUT /api/skills/user-skills/<platform id>` and from `commit_skill` of an accepted propose_skill (online ACE drafts these for platform skills such as `wiki`); Skill Studio's own Save uses the workshop path, which was already safe. :8000 serves this checkout, so an accepted commit would have rewritten the repo runbook and dropped its tools; `git status` on qa was clean, so it has not happened.
- Skill Studio's description field says "<= 60 chars" and cuts the shown value at 60, but the API saves longer descriptions (the QA copy's was ~100 chars); the field then shows a truncated value.
- No shipped agent ticks the `wiki` skill (AutoReiv has wiki-knowledge, wiki-curation, wiki-inbox, wiki-templates), so `skill_view("wiki")` is refused for AutoReiv; the live load check used `wiki-knowledge`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| PUT /api/skills/user-skills/wiki on :8770 (temp data folder) | API | pass | 200; copy at `scratch/live_qa_data/skills/wiki/SKILL.md` with all 11 tools and `based_on`; origin user; repo and sandbox `git status` clean; platform file hash unchanged |
| Same for wiki-knowledge, then AutoReiv chat "skill_view wiki-knowledge, quote the QA-611 marker" | desktop | pass | one skill_view call; its result has the marker and the reply quotes it (the agent loads the data copy); AutoReiv's wiki tools unchanged |
| Skill Studio > wiki-knowledge > Use shipped version | desktop | pass | "back to the shipped version"; data copy removed; skill loads from platform again without the marker; platform file unchanged |

Live on :8770, nemotron-3.5-lightning (Spark), 2026-10-03 11:40-11:46 ET.

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003e\skill-studio-wiki-knowledge-data-copy-desktop.png`, `...\chat-skill-view-wiki-knowledge-data-copy-desktop.png`, `...\skill-studio-wiki-knowledge-use-shipped-desktop.png`, `...\skill-studio-wiki-data-copy-desktop.png`.

## Release note
Saving a skill that shares a name with a built-in skill no longer overwrites the built-in runbook; your copy is saved in your data folder.
