---
id: CARD-714
title: "Decompose src/domain/wiki/store.py (2,137 lines), fix double vault file parsing in graph/mindmap, and remove upward domain imports"
type: feature
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-714-wiki-store-decomposition]
  checks: [tests/unit/wiki/test_card714_wiki_store_modularization.py]
branch: feat/card-714-wiki-store-decomposition
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-714 Decompose src/domain/wiki/store.py (2,137 lines), fix double vault file parsing in graph/mindmap, and remove upward domain imports

## Intent
`src/domain/wiki/store.py` is 2,137 lines and violates both the 800-line ceiling and domain layer purity by embedding 460 lines of static markdown templates, importing `EDUCATION_TEMPLATES` from `src.application.education.templates` and `DataDirResolver` from `src.infrastructure.data.resolver`, and reading/parsing every `.md` file in the vault twice per call in `get_graph()` and `get_mindmap()`.

## Goal
1. Zero imports from `src.application.*` or `src.infrastructure.*` anywhere in `src/domain/` (enforced by a guard test).
2. `src/domain/wiki/store.py` is split into focused modules (<800 lines each): static templates, vault scaffolding/migration, note & template CRUD, and vault graph/mindmap/tree indexing.
3. `get_graph()` and `get_mindmap()` read each markdown file once per call instead of twice.

## Change
- Extract the 460 lines of template constants out of `src/domain/wiki/store.py` into `src/domain/wiki/templates_catalog.py`, and move education template definitions so `src/domain/` never imports from `src/application/`.
- Inject the resolved root path (or resolver callback) from the application/infrastructure layer so `src/domain/wiki/` never imports `src.infrastructure.data.resolver`.
- Split vault graph, mindmap, tree, and search indexing out of `src/domain/wiki/store.py` into `src/domain/wiki/graph_index.py` and eliminate the double file read in `get_graph()` and `get_mindmap()`.
- Add an AST architecture guard test asserting `src/domain/` never imports from `src.application`, `src.infrastructure`, or `src.web`.

## What dies
- Upward imports from `src.application` and `src.infrastructure` inside `src/domain/wiki/store.py`.
- Redundant second `read_text()` + frontmatter parse pass over every vault note in `get_graph()` and `get_mindmap()`.

## Proof
- Journey `card-714-wiki-store-decomposition`:
  1. Open Wiki Studio (`#view-wiki`), create/read a note, and open the Wiki Mind-Map / Graph view on desktop and phone.
- Checks:
  - `tests/unit/wiki/test_card714_wiki_store_modularization.py`

## Plan and decisions
- Phase 3 domain purity and monolith decomposition.

## Findings
- None yet.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-714\...`

## Release note
- Split `src/domain/wiki/store.py` (2,137 lines) into focused modules under 800 lines, eliminated double vault file reads in `get_graph`/`get_mindmap`, and enforced zero upward imports in `src/domain/` [CARD-714].
