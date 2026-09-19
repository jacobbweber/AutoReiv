# Tasks Specification: Mobile-First Responsive Layout & Viewport Overhaul

> **Document ID**: `TASKS-RESP-001`  
> **Status**: In Progress  
> **Traceability ID**: `[REQ-RESP-001]`, `[REQ-RESP-002]`, `[REQ-RESP-003]`

---

## Vertical Slices

- [ ] **Slice 1: Dynamic Viewport & Chat Studio Sticky Bar**
  - [ ] Task 1.1: `[REQ-RESP-001]` Update `index.html` root `<html>`, `<body>`, and `<main>` containers to enforce `h-[100dvh]` viewport bounds without page scroll.
  - [ ] Task 1.2: `[REQ-RESP-001]` Structure `#view-chat` with `flex-1 overflow-y-auto` messages stream and `sticky bottom-0 flex-shrink-0` input container.
  - [ ] Task 1.3: `[REQ-RESP-001]` Add unit tests in `tests/unit/web/test_mobile_responsive.py`.

- [ ] **Slice 2: Responsive Off-Canvas Drawers for Wiki & System Info**
  - [ ] Task 2.1: `[REQ-RESP-002]` Add mobile toggle buttons (`#wikiMobileDrawerBtn`, `#docsMobileDrawerBtn`) to Wiki Studio and System Info headers.
  - [ ] Task 2.2: `[REQ-RESP-002]` Update `app.js` to handle off-canvas drawer open/close and auto-dismiss on note/topic selection.

- [ ] **Slice 3: Mobile Touch Modals, Mind Map & Pre-Flight Quality Gates**
  - [ ] Task 3.1: `[REQ-RESP-003]` Make `#wikiMindMapModal`, `#wikiNewNoteModal`, and `#routineModal` responsive fullscreen/sheet on mobile screens.
  - [ ] Task 3.2: `[REQ-RESP-003]` Add touch event listeners to Mind Map canvas for smooth mobile dragging and pan/zoom.
  - [ ] Task 3.3: `[REQ-RESP-003]` Run pre-flight DoD quality gates.
