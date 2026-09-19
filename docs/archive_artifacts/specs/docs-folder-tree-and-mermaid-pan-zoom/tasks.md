# Implementation Tasks: System Documentation Folder Tree & Mermaid Pan-Zoom Inspector

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-DOCS-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: Nested Navigation Tree Data Contract (`[REQ-DOCS-001]`)
- [x] **Task 1.1**: [RED] Write unit test for nested directory hierarchy generation in `tests/unit/web/test_system_docs_service.py`.
- [x] **Task 1.2**: [GREEN] Update `SystemDocumentationService.get_navigation_tree()` in `src/application/web/system_docs_service.py` to return recursive folder tree.

### Slice 2: Interactive Collapsible Tree Sidebar UI (`[REQ-DOCS-002]`)
- [x] **Task 2.1**: Update `src/web/templates/index.html` and `src/web/static/app.js` with recursive folder tree renderer, expand/collapse toggles, and live search filtering.

### Slice 3: Interactive Mermaid Diagram Overlay & Inspector Modal (`[REQ-DOCS-003]`, `[REQ-DOCS-004]`)
- [x] **Task 3.1**: Add `#mermaidZoomModal` dialog to `src/web/templates/index.html` with PTZ canvas viewport and zoom toolbar.
- [x] **Task 3.2**: Implement Pan-Tilt-Zoom engine in `src/web/static/app.js` with mouse drag, wheel zoom, zoom slider, reset view, and attach hover inspect buttons to rendered Mermaid diagrams.

### Slice 4: Verification, Pre-Flight Gates & Session Wrap-Up
- [x] **Task 4.1**: Run full test suite (`pytest`) and linting (`ruff check .`).
- [x] **Task 4.2**: Verify RTM integrity (`verify_rtm.py --pre-flight` with all 110 requirements passing).
- [x] **Task 4.3**: Live test folder navigation and interactive Mermaid PTZ inspection in browser.
