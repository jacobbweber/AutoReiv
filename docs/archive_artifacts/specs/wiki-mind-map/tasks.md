# Tasks Specification: Wiki Studio Interactive Mind Map & Tree Navigation

> **Document ID**: `TASKS-WIKI-MINDMAP-001`  
> **Status**: In Progress  
> **Traceability ID**: `[REQ-MIND-001]` through `[REQ-MIND-003]`

---

## Vertical Slices

- [ ] **Slice 1: Tree Navigation Fixes (Degree & Subject Level Expansion)**
  - [ ] Task 1.1: `[REQ-MIND-001]` Update `renderWikiTree()` in `src/web/static/app.js` to render Degree (`domain`) and Subject (`topic`) folders as interactive collapsible buttons with chevrons and persistent memory.

- [ ] **Slice 2: Multi-Dimensional Mind Map API & Domain Store**
  - [ ] Task 2.1: `[REQ-MIND-002]` Add `get_mindmap(include_tags=True, include_taxonomy=True)` to `WikiStore` in `src/domain/wiki/store.py` and `WikiService` in `src/application/wiki/service.py`.
  - [ ] Task 2.2: `[REQ-MIND-002]` Add `GET /api/wiki/mindmap` REST endpoint in `src/web/app.py`.
  - [ ] Task 2.3: `[REQ-MIND-002]` Add unit tests in `tests/unit/wiki/test_wiki_mindmap.py` and `tests/unit/web/test_wiki_api.py`.

- [ ] **Slice 3: Obsidian-Style Interactive Mind Map 2D Physics Canvas UI**
  - [ ] Task 3.1: `[REQ-MIND-003]` Add `[🧠 Mind Map]` button and `#wikiMindMapModal` with HTML5 Canvas, search input, dimension toggle pills, and physics controls in `src/web/templates/index.html`.
  - [ ] Task 3.2: `[REQ-MIND-003]` Implement the full 2D force-directed canvas physics engine, pan/zoom, hover tooltips, and click-to-open handlers in `src/web/static/app.js`.
  - [ ] Task 3.3: `[REQ-MIND-003]` Update RTM matrix, run pre-flight verification, merge to `qa`, and deliver runbook.
