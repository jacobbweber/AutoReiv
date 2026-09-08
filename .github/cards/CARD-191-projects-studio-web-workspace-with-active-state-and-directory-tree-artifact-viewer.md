# [CARD-191] Projects Studio Web Workspace with Active State and Directory Tree Artifact Viewer

> **Status**: Ready
> **Created**: 2026-09-08
> **Spec Reference**: none
> **Labels**: `type:feature`, `area:web`, `area:projects`

---

## 1. Why / Intent
Transform Projects Studio from a simple directory table into an interactive web workspace. Replace ambiguous "Open" language with explicit "Set as Active" action, display a persistent `[Active Project]` indicator badge, and provide a two-pane layout: directory tree on the left and rich artifact viewer on the right. This allows the operator to visually inspect, browse, and read project cards, specifications, steering, ADRs, and source scripts as the Developer agent creates and updates them.

---

## 2. What to Build

### A. Active Project State & Controls
1. **Language Standardization**:
   - Replace "Open" button in project rows with **"Set as Active"**.
   - Show a persistent, prominent badge **`[Active Project]`** on the currently active project.
2. **Project Header Bar**:
   - Displays current active project name, folder path, quick switch dropdown, and a manual Refresh button to reload tree changes after agent turns.

### B. Directory Tree Explorer (Left Pane)
1. **Hierarchical Tree Navigation**:
   - Displays project root contents hierarchically with expand/collapse directory toggles.
   - Differentiates folders, markdown documents, and code files with distinct iconography.
2. **Category Quick Filters**:
   - Quick navigation bar at the top of the tree to jump straight to:
     - **All Files** (full root)
     - **Cards** (`.agents/cards/`)
     - **Specs** (`.agents/specs/`)
     - **Steering** (`.agents/steering/`)
     - **ADRs** (`.agents/adr/`)

### C. Artifact & File Viewer (Right Pane)
1. **Rich Markdown Viewer**:
   - Renders markdown files with formatted headers, task checkboxes, tables, blockquotes, and fenced code blocks.
2. **Plaintext / Script Viewer**:
   - Displays source code files (`.ps1`, `.py`, `.ts`, `.json`) with line numbers and monospace font.
3. **Empty / Welcome State**:
   - Displays project metadata summary (total cards, specs, and status) when no file is selected.

### D. Backend Endpoints
- Connect web UI to project file tools endpoints (`/api/projects/files/list` and `/api/projects/files/read`) ensuring strict jailed path resolution under the active project root.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Projects Studio displays **"Set as Active"** button and renders **`[Active Project]`** badge on the selected project.
- [ ] Selecting a project immediately opens the workspace view for that project.
- [ ] Directory tree explorer correctly lists folders and files under the active project root.
- [ ] Category quick filters jump directly to `.agents/cards`, `.agents/specs`, `.agents/steering`, and `.agents/adr`.
- [ ] Clicking any file in the tree displays its content in the viewer pane (formatted markdown for `.md`, clean monospace for scripts).
- [ ] Refresh button re-scans the directory tree without full page reload.
- [ ] Unit and frontend contract tests pass cleanly via automated test runner.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Jailed path security: all file operations remain strictly clamped inside the active project root.
- Pure vanilla JS and CSS adhering to existing AutoReiv design tokens and theme.
- Card remains `Ready` until user says `build`.
