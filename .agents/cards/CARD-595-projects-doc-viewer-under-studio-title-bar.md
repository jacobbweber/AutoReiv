---
id: CARD-595
title: "Projects studio: an open document's header (close) is hidden behind the studio window title bar"
status: In Review
created: 2026-10-01
branch: card/595-projects-doc-viewer-header
related:
  - CARD-303
labels:
  - type:bug
  - area:frontend
  - area:projects
  - P2
needs_decision: none
---

# [CARD-595] Projects studio: an open document's header is hidden behind the studio window title bar

> **Status**: In Review (branch `card/595-projects-doc-viewer-header`, off qa `42fa22cd`; not merged)
> **Created**: 2026-10-01
> **Reported by**: Jacob (live UI)
> **Labels**: `type:bug`, `area:frontend`, `area:projects`, `P2`

---

## 1. Four Beats

### Beat 1: What Jacob means
When I open a document in Projects studio, I need to see and click both the document's own close button and the studio window's minimize and close buttons.

### Beat 2: What AutoReiv does now (before)
Below 768 px wide (phone, or a narrow browser window), `#projectsViewerPane` was `fixed inset-0 z-50`. It covered the whole viewport, so the hosted studio's window title bar (`.desktop-win-titlebar`, which has a higher z-index) sat on top of the viewer header. The viewer's close button was covered by the studio `desktop-win-close` button. At wide sizes the pane is a side column, so there was no overlap.

### Beat 3: What changes
The viewer overlay is `absolute inset-0 z-30` inside `#projectsExplorerView` (now `relative`). It fills only the studio content area, below the studio title bar. There are no JS changes; `projects.js` still toggles `hidden`/`flex` with `isMobile()`.

### Beat 4: How we know
Live check on a throwaway `:8770` clone, plus smoke **TC-47** (desktop 1280, narrow 760, phone 390). TC-47 fails on qa `42fa22cd` (narrow and phone) and passes with the fix.

## 2. Requirements (EARS)

- **REQ-595-001**: WHEN a document is open in Projects studio at any viewport size, the viewer header SHALL sit fully below the studio window title bar.
- **REQ-595-002**: WHEN a document is open, the viewer close button, the studio minimize button and the studio close button SHALL each be the top element at their centre point and SHALL work when clicked.
- **REQ-595-003**: The mobile viewer overlay SHALL be confined to the studio content area (`#projectsExplorerView`), not the viewport.

## 3. Evidence

Screenshots are in `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1001\`:
- `projects-doc-before.png`: phone 390 on qa; the viewer header is hidden under the "Projects" title bar. Also `projects-doc-before-narrow.png`, plus `projects-doc-before-desktop-wide-no-repro.png` (at 1400 the pane is a side column, so there is no bug).
- `projects-doc-after-desktop.png`, `projects-doc-after-maximized.png`, `projects-doc-after-phone.png` (plus `-narrow`).

Playwright clicks, after the fix, at desktop, maximized, phone and narrow:
- viewer close: pane cleared (desktop) or hidden (mobile);
- studio minimize: view hidden; reopened from the dock;
- studio close: view hidden;
- 0 page errors.

## 4. Changes
- `src/web/templates/index.html`: `#projectsViewerPane` changed from `fixed inset-0 z-50` to `absolute inset-0 z-30`. `#projectsExplorerView` gets `relative`.
- `tests/e2e/smoke.spec.js`: new TC-47 (mocked `/api/projects*` routes).
