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

- `worker_tools.py`: `_promotion_path()`: the note goes to `00_Inbox/<name>.md` (One-Door Policy; the curator
  graduates it to 01_Notes). A path already under a vault folder (`00_Inbox/`, `01_Notes/`, `02_Resources/`,
  `03_Archive/`) is kept; a model-invented folder (`reports/fixture-scan`, seen live on the rerun) is dropped to the
  inbox too. Backslashes normalized. `test_worker_tools.py` now reads the promoted note from `00_Inbox/`.
- Tests: `tests/unit/skills/test_card590_promote_artifact_inbox.py`.

## Acceptance

- [x] Bare or invented-folder slug -> `00_Inbox/<name>.md`, nothing at the root; vault-folder paths kept.
- [x] Live: ar-11 promotion lands in 00_Inbox/ (see Log).

## Log

- 2026-09-30: built on the branch with tests.
- 2026-09-30: live rerun: AutoReiv passed `reports/fixture-scan` and got a new top-level `reports/` folder, so
  invented folders now go to the inbox as well.
- 2026-09-30 (live, throwaway :8770 on qa + 589/590/591, nemotron): ar-11 scan -> artifact -> promote landed at `00_Inbox/fixtures.md`; nothing at the root.
