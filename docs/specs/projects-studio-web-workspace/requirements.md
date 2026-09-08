# Requirements: Projects Studio Web Workspace with Active State and Directory Tree Artifact Viewer

## User Stories & EARS Requirements

### 1. Active Project State & Explicit Selection
- **User Story**: As an operator managing multiple software projects, I want an explicit "Set as Active" action and a persistent indicator showing which project is currently active, so that I have absolute clarity on which codebase Developer agent turns and file operations apply to.
- **[REQ-PROJ-010]**: When viewing the project list in Projects Studio, each project item shall display an explicit "Set as Active" action button, and the currently active project shall render a distinct, persistent `[Active Project]` green badge.

### 2. Two-Pane Workspace Layout
- **User Story**: As an operator inspecting an active project, I want a dual-pane workspace with a directory explorer on the left and an artifact/file viewer on the right, so that I can browse and read files without leaving the studio or opening an external tool.
- **[REQ-PROJ-011]**: When an active project is selected, Projects Studio shall display a two-pane layout featuring an interactive Directory Tree on the left and an Artifact & File Viewer on the right.

### 3. Directory Tree Navigation & Quick Filters
- **User Story**: As an operator reviewing project artifacts, I want collapsible directory navigation and one-click filter buttons for cards, specs, steering, and ADRs, so that I can quickly navigate to relevant agent deliverables.
- **[REQ-PROJ-012]**: The Directory Tree explorer shall provide directory collapse/expand toggles and quick filter buttons for **All**, **Cards** (`.agents/cards/` or `.github/cards/`), **Specs** (`.agents/specs/` or `docs/specs/`), **Steering** (`.agents/steering/`), and **ADRs** (`.agents/adr/` or `docs/adr/`), allowing instant scoping of visible tree entries.

### 4. Artifact & File Viewer
- **User Story**: As an operator reading project files, I want Markdown files rendered formatted and code scripts displayed in clean monospace with copy actions, so that I can review specifications and code with high readability.
- **[REQ-PROJ-013]**: When a file is selected from the tree, the right pane shall render Markdown files (`.md`) formatted using the Markdown parser, and code/text files (`.py`, `.ps1`, `.json`, `.yaml`, etc.) in a styled monospace container with file metadata and copy action.

### 5. Jailed File API Endpoints
- **User Story**: As an API consumer and frontend studio, I want secure endpoints to list and read files within the active project root, so that client browsing is responsive and strictly isolated from host filesystem escape.
- **[REQ-PROJ-014]**: The backend shall expose `GET /api/projects/files/list` and `GET /api/projects/files/read` endpoints strictly clamped to the active project root, filtering out `.git`, `__pycache__`, `node_modules`, and `.venv` by default, and rejecting all traversal escapes.
