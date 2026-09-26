---
id: CARD-521
title: "Bundled seed skills in the data dir are copied once and never updated, so shipped fixes never reach existing installs"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-497
  - CARD-426
  - ADR-0056
labels:
  - type:bug
  - area:skills
  - P3
---

# [CARD-521] Bundled seed skills never receive shipped updates

> **Status**: Ready (found while refining CARD-497, 2026-09-26 ~9:50 AM ET, qa `51b6402b`). Not recommended as next: it does not damage data or block current work, and CARD-497 D10 handles the one stale file that matters now (`build-agent-pack`) with a hash-matched rewrite.
> **Related**: CARD-497 (D10), CARD-426 (the same one-off rewrite for `native-tool-engineering`), ADR-0056 (platform pack refresh)
> **Labels**: `type:bug`, `area:skills`, `P3`

## Problem

`seed_bundled_skill_packs` (`src/infrastructure/skills/seed.py` L67-84) copies each bundled `SKILL.md` into `$DATA/skills/<id>/` **only when it is missing** and never updates it ("user edits stay"). Platform packs are refreshed on startup unless `user_modified` (`platform_pack_promotion.py`), but these root seeds are not, so a wording or safety fix in `src/infrastructure/skills/seeds/` never reaches an existing install.

Concrete case: Developer is allowed `build-agent-pack` but its pack has no copy, so it reads `$DATA/skills/build-agent-pack/SKILL.md`. On Jacob's install that file still says tools are "trained in the Factory" and "Factory Studio owns training and wiring new callables", which is wrong for the tool builder itself. CARD-426 already needed a one-off rewrite for the same reason.

Jacob's `$DATA/skills` has 11 seed dirs (`build-agent-pack`, `coordination`, `education-*`, `proposals`, `sandbox`, `sqlite-storage`, `wiki`, `worker`).

## Change (to refine)

Record the hash of each seed as shipped (a small manifest written next to the copy). On startup, replace a seed whose current hash equals the recorded shipped hash when the bundled version differs; leave edited copies alone and report them once (log, and optionally the Skill Studio list). Replace the CARD-426 and CARD-497 one-off rewrites with this.

## Done when

A shipped seed change reaches unedited installs on the next start; edited seeds are never overwritten; tests cover unedited, edited and missing copies.
