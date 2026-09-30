---
id: CARD-590
title: "promote_artifact_to_wiki files a bare slug into 00_Inbox/ instead of the vault root"
status: In Review
created: 2026-09-30
branch: card/590-promote-artifact-inbox
related:
  - CARD-582
labels:
  - type:bug
  - area:wiki
  - P3
needs_decision: none
milestone: M24
---

# [CARD-590] promote_artifact_to_wiki files a bare slug into 00_Inbox/ instead of the vault root

> **Status**: In Review
> **Labels**: `type:bug`, `area:wiki`, `P3`

## Why

2026-09-30 battery (ar-11, first run of batch_worker_scan -> get_session_artifact -> promote_artifact_to_wiki): the
promoted note landed at the vault root (`fixture-scan.md`), outside `00_Inbox/ 01_Notes/ 02_Resources/`; the wiki
overview then listed it as a stray top-level file. The tool wrote `<wiki_slug>.md` as given.

## Change

- `worker_tools.py`: `_promotion_path()`: a bare slug goes to `00_Inbox/<slug>.md` (One-Door Policy; the curator
  graduates it to 01_Notes); a slug with a folder is kept (`reports/audit` -> `reports/audit.md`), backslashes
  normalized.
- Tests: `tests/unit/skills/test_card590_promote_artifact_inbox.py`.

## Acceptance

- [x] Bare slug -> `00_Inbox/<slug>.md`, nothing at the root; folder slugs kept.
- [ ] Live: ar-11 promotion lands in 00_Inbox/ (see Log).

## Log

- 2026-09-30: built on the branch with tests.
