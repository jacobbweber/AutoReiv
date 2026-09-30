---
id: CARD-552
title: "read_document_file reads any path on disk (no path guard)"
status: Done
completed: 2026-09-30
created: 2026-09-27
branch: qa
related:
  - CARD-539
  - CARD-550
labels:
  - type:bug
  - area:tools
  - P2
needs_decision: none
milestone: M24
---

# [CARD-552] read_document_file has no path guard

> **Status**: Done (merged into qa 2026-09-30)
> **Related**: CARD-539 (D3 made it a required platform tool), CARD-550
> **Labels**: `type:bug`, `area:tools`, `P2`

## Evidence

In the first CARD-550 live QA run (desktop and phone), the ask was "read src/application/agent_packs/allowed_tools.py from the AutoReiv checkout". AutoReiv did not hand off to Developer. It answered by itself with `read_document_file`, which is a required platform tool on every agent (CARD-539 D3). `extract_document` opens any `.py`, `.json`, `.log` or other text path on disk. It has no root check like `repo_file_read` (checkout root) or `read_project_file` (project root). So any agent can read any file the serve process can read, including files outside the checkout and outside the AutoReiv data folder, without asking for approval.

## Change

Limit `read_document_file` to allowed roots: uploads, the wiki vault, the active project and the data folder. For any other path, return a clear error that names the right tool (`repo_file_read` on Developer for the checkout). A unit test checks that a path outside the roots is refused and that an upload is still read.

## Done when

The unit test passes. A live QA ask to read a checkout `.py` file through AutoReiv no longer gets the file contents from `read_document_file`.

## Outcome (2026-09-30)

- `read_document_file` resolves the path against allowed roots, read at call time: the data folder (attachments live
  there), the wiki vault, the selected project and the OS scratch folder. Relative paths are tried under each root.
- Anything else (including `..` escapes) is refused with a message that names `repo_file_read` (Developer) and
  `read_project_file`. Database, key/cert and `.env` files are refused even inside a root.
- Tests: `tests/unit/skills/test_card552_document_path_guard.py`; extractor test passes its root.
- 2026-09-30: preflight --fast --base qa GREEN. Jacob: merge to qa (small engineering fix). Done; merged into qa.
