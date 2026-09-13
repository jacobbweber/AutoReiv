# [CARD-138] App Shell Slim Rail and Dual-Pane Workbench Canvas

> **Status**: Done
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
AutoReiv is evolving into a high-performance, focused Multi-Agent Control Plane. The previous permanent 280px sidebar consumed valuable horizontal screen width, and artifacts (markdown plans, code snippets, execution journeys) were pushed into the vertical message stream. This card implements an ergonomic App Shell:
- A modern **52px Slim Icon Rail** on desktop that frees up over 220px of horizontal workspace.
- A **Dual-Pane Workbench Canvas** where artifacts open side-by-side with conversation on desktop.
- A **Mobile Pop-Out Sheet / Drawer** where artifacts open smoothly in full-width drawer mode with a single tap.
- 100% preservation of all existing DOM IDs, testing contracts, and studio capabilities.

---

## 2. Requirements (EARS)

- **[REQ-SHELL-001]** *When* on desktop view (> 1024px), the application *shall* display a 52px slim icon rail (`#appRail`) with quick surface switchers for Cockpit (`#railBtnChat`), Vault (`#railBtnVault`), Fleet (`#railBtnFleet`), and Settings (`#railBtnSettings`).
- **[REQ-SHELL-002]** *While* the user is in Chat Cockpit, the application *shall* provide a toggleable session drawer (`#sessionDrawer`) to view and switch conversations without eating permanent workspace.
- **[REQ-SHELL-003]** *When* an agent creates an artifact or the user clicks an artifact chip, the application *shall* open the Dual-Pane Workbench Canvas (`#chatWorkbenchPane`):
  - Side-by-side with chat on desktop (> 1024px).
  - Full-screen pop-out drawer with back button on mobile (< 1024px).
- **[REQ-SHELL-004]** *While* the Workbench Canvas is open, the user *shall* have access to Preview (`#workbenchTabPreview`), Raw (`#workbenchTabRaw`), Copy (`#workbenchCopyBtn`), Save to Wiki (`#workbenchSaveWikiBtn`), and Close (`#workbenchCloseBtn`).
- **[REQ-SHELL-005]** *The system shall* preserve 100% of existing studio tab IDs (`#tab-chat`, `#tab-routines`, `#tab-observability`, `#tab-agents`, `#tab-settings`, `#tab-wiki`, `#tab-projects`) and DOM selectors to guarantee zero test regressions.

---

## 3. Acceptance Criteria
- [x] 52px slim icon rail implemented in `index.html` with active indicators.
- [x] Session flyout drawer allows switching and creating sessions.
- [x] Dual-Pane Workbench Canvas implemented with responsive side-by-side (desktop) and pop-out sheet (mobile).
- [x] Workbench supports Markdown preview, raw view, copy to clipboard, and save to Wiki.
- [x] All 103 Vitest frontend unit tests pass.
- [x] All 73 FastAPI web integration tests pass.
- [x] Zero ESLint errors.
- [x] Requirements Traceability Matrix (`docs/rtm.json`) synchronized.
