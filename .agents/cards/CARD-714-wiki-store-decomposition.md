---
id: CARD-714
title: "Decompose src/domain/wiki/store.py (2,137 lines), fix double vault file parsing in graph/mindmap, and remove upward domain imports"
type: feature
status: In Review
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-714-wiki-store-decomposition]
  checks: [tests/unit/wiki/test_card714_wiki_store_modularization.py]
branch: feat/card-714-wiki-store-decomposition
log: {minutes: 20, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-714 Decompose src/domain/wiki/store.py (2,137 lines), fix double vault file parsing in graph/mindmap, and remove upward domain imports

## Intent
`src/domain/wiki/store.py` was 2,125 lines and violated both the 800-line ceiling and domain layer purity by embedding 460 lines of static markdown templates, importing `EDUCATION_TEMPLATES` from `src.application.education.templates` and `DataDirResolver` from `src.infrastructure.data.resolver`, and reading/parsing every `.md` file in the vault twice per call in `get_graph()` and `get_mindmap()`.

## Goal
1. Zero imports from `src.application.*`, `src.infrastructure.*`, or `src.web.*` anywhere in `src/domain/` (enforced by a guard test).
2. `src/domain/wiki/store.py` is split into focused modules (<800 lines each): static templates, education templates, vault scaffolding/migration/template CRUD, note CRUD, and vault graph/mindmap/tree indexing.
3. `get_graph()` and `get_mindmap()` read each non-template markdown file once per call instead of twice.

## Change
- Created `src/domain/data_root.py` (80 lines) for domain-level user-data root resolution and checkout-hygiene validation hooks, registered by `src/infrastructure/data/resolver.py`, removing `src.infrastructure` imports from `src/domain/wiki/store.py` and `src/domain/security/vault.py`.
- Moved `EDUCATION_TEMPLATES` and helpers into `src/domain/wiki/education_templates.py` (525 lines) and turned `src/application/education/templates.py` into a thin re-export facade.
- Extracted static structured templates into `src/domain/wiki/templates_catalog.py` (578 lines), vault scaffolding/migration/template CRUD into `src/domain/wiki/vault_migration.py` (471 lines), and single-pass vault graph, mindmap, tree, and search indexing into `src/domain/wiki/graph_index.py` (467 lines), shrinking `src/domain/wiki/store.py` from 2,125 lines to 771 lines.
- Eliminated the redundant second `read_text()` + frontmatter parse pass over vault notes in `get_graph()` and `get_mindmap()` via `_scan_non_template_notes_with_links()`.

## What dies
- Upward imports from `src.application` and `src.infrastructure` inside `src/domain/wiki/store.py` and `src/domain/security/vault.py`.
- Redundant second `read_text()` + frontmatter parse pass over every vault note (plus unnecessary reads of template files) in `get_graph()` and `get_mindmap()`.

## Proof
- Journey `card-714-wiki-store-decomposition`:
  1. Verifies WikiStore note CRUD, templates catalog, single-pass graph, and multi-dimensional mindmap APIs.
  2. Opens Wiki Studio (`#view-wiki`), renders the created note, opens the Mind-Map modal (`#wikiMindMapModal` / `#wikiMindMapCanvas`), and verifies responsive layout on desktop and phone.
- Checks:
  - `tests/unit/wiki/test_card714_wiki_store_modularization.py`

## Plan and decisions
- Phase 3 domain purity and monolith decomposition.

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-714-wiki-store-decomposition` | desktop (`1440x900`) | PASS | 3/3 steps passed (CRUD, templates, graph, mindmap modal) |
| `card-714-wiki-store-decomposition` | phone (`390x844`) | PASS | 3/3 steps passed |

Screenshots:
- `/tmp/autoreiv-qa/card-714/card-714-wiki-store-decomposition-desktop-02-open-wiki-studio-view-wiki-and-verify-note-rende.png`
- `/tmp/autoreiv-qa/card-714/card-714-wiki-store-decomposition-desktop-03-open-wiki-mind-map-modal-and-verify-canvas-and-l.png`
- `/tmp/autoreiv-qa/card-714/card-714-wiki-store-decomposition-phone-02-open-wiki-studio-view-wiki-and-verify-note-rende.png`

## Release note
- Split `src/domain/wiki/store.py` (2,125 lines) into focused modules under 800 lines, eliminated double vault file reads in `get_graph`/`get_mindmap`, and enforced zero upward imports in `src/domain/` [CARD-714].
