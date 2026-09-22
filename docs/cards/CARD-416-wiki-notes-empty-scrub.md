---
id: CARD-416
title: "Wiki establish: scrub polluted 01_Notes taxonomy dirs; keep Notes empty"
status: Ready
created: 2026-09-21
investigation: docs/design/CARD-416-wiki-notes-scrub-investigation.md
labels:
  - type:bug
  - area:wiki
  - area:test
---

# [CARD-416] Wiki establish: scrub polluted 01_Notes taxonomy dirs; keep Notes empty

> **Status**: Ready  
> **Created**: 2026-09-21  
> **Investigation**: [docs/design/CARD-416-wiki-notes-scrub-investigation.md](../../docs/design/CARD-416-wiki-notes-scrub-investigation.md)  
> **Labels**: `type:bug`, `area:wiki`, `area:test`

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **continue** | Refine acceptance before code |
| **build** | Start implementation on a feat branch from `qa` |
| **merge to qa** | After In Review + live test |

---

## 1. Four Beats

### Beat 1 - What Jacob means

When a wiki is established, `01_Notes` must be empty. No domain/topic trees such as `computer_science/artificial_intelligence`, `general/notes`, `operations/diagnostics`, `operations/worklog`, or `systems_engineering/observability`. Stale code, seeds, and tests that expect those folders must be scrubbed.

### Beat 2 - What AutoReiv does now

Pre-CARD-406 `WikiStore.scaffold()` created exactly those five paths (and starter notes). CARD-406 already stopped creating them on **fresh** vaults (`01_Notes` is bare; starter seed is a no-op). Existing vaults keep empty children forever because scaffold only `mkdir(..., exist_ok=True)` and never deletes. Vanilla tests assert no `.md` under Notes, not “no subdirectories,” so empty pollution survives unnoticed. Re-running scaffold / boot / Settings confirm leaves leftovers in place.

### Beat 3 - What will change

1. Idempotent scrub of the known empty seed taxonomy paths (and empty parents) from `scaffold` and/or `cleanup_vault` / Settings confirm_scaffold.
2. Strengthen `test_vanilla_wiki_seeding` to require `01_Notes` has zero children.
3. Regression test: plant the five empty dirs → scrub/scaffold → gone; non-empty real notes kept.
4. Do not reintroduce domain mkdir lists; leave tag-authority text under `_Templates` as documentation only.

### Beat 4 - What dies today

- Empty seed taxonomy dirs under `01_Notes` surviving forever
- Tests that only check for `.md` and miss empty dir pollution
- Any remaining code/docs that treat those five paths as required scaffold layout

---

## 2. Acceptance

- [ ] Fresh scaffold: `01_Notes` has no children.
- [ ] Vault with only the five empty seed paths: after scrub/scaffold, gone.
- [ ] Non-empty operator notes under `01_Notes` are not deleted.
- [ ] Settings “Create standard folder layout” does not recreate the five-pack.
- [ ] Tests green; CHANGELOG Unreleased.

## 3. Out of scope

- Chat Studio durability (CARD-415)
- Deleting operator-authored notes
- Redesigning domain/topic taxonomy for curated warehouse notes
- CARD-414 merge (separate)

## 4. Files likely to touch

`src/domain/wiki/store.py`, `tests/unit/wiki/test_vanilla_wiki_seeding.py`, optional scrub regression test, CHANGELOG.

## 5. Branching

`feat/card-416-wiki-notes-empty-scrub` from `qa` (can land independently of 415; small and safe after or alongside 414).
