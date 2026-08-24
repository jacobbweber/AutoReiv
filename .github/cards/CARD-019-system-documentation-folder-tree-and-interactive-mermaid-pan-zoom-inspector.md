# [CARD-019] System Documentation Folder Tree and Interactive Mermaid Pan Zoom Inspector

> **Status**: Completed  
> **Created**: 2026-08-23  
> **Spec Reference**: `docs/specs/docs-folder-tree-and-mermaid-pan-zoom/`  
> **ADR**: `docs/adr/0020-system-documentation-folder-tree-and-interactive-mermaid-pan-zoom-inspector.md`  
> **Labels**: `type:feature`, `component:web`, `sdlc:milestone-19`

---

## 1. Why / Intent
Enable seamless exploration of platform architecture and specifications by organizing documents into a collapsible folder tree and providing an interactive Pan-Tilt-Zoom (PTZ) modal for high-resolution inspection of Mermaid architecture diagrams.

---

## 2. What to Build
- Nested navigation tree data contract in `SystemDocumentationService.get_navigation_tree()` (`[REQ-DOCS-001]`).
- Collapsible directory tree UI with folder expand/collapse state in `#docsNavTree` (`[REQ-DOCS-002]`).
- Interactive hover overlay buttons (`[🔍 Inspect & Zoom]`) on rendered Mermaid diagrams (`[REQ-DOCS-003]`).
- Pan-Tilt-Zoom (PTZ) engine modal (`#mermaidZoomModal`) with mouse wheel zoom, click-and-drag pan, reset, and fullscreen toggles (`[REQ-DOCS-004]`).

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-DOCS-001]`: Nested directory tree JSON API for specs, ADRs, and SDLC rules.
- [x] `[REQ-DOCS-002]`: Interactive collapsible folder sidebar in `#view-docs`.
- [x] `[REQ-DOCS-003]`: Interactive hover button and click inspection modal for Mermaid diagrams.
- [x] `[REQ-DOCS-004]`: Smooth PTZ controls (wheel zoom 0.2x-5.0x, drag pan, reset, fullscreen).
- [x] 211 automated tests passing via `pytest`.
- [x] Zero lint errors via `ruff check .`.
- [x] 110 requirements passing in RTM via `verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
