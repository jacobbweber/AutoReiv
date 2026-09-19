# Tasks: Projects Studio Web Workspace with Active State and Directory Tree Artifact Viewer

## Vertical Slices

### Slice 1: Backend Jailed File Endpoints (`[REQ-PROJ-014]`)
- [x] Task 1.1 (Red Test): Write failing integration tests in `tests/integration/test_projects_api.py` for `/api/projects/files/list` and `/api/projects/files/read` with category filtering and path jail enforcement.
- [x] Task 1.2 (Green Implementation): Implement `GET /api/projects/files/list` and `GET /api/projects/files/read` in `src/web/routers/projects.py`.
- [x] Task 1.3 (Refactor/Verification): Run pytest and confirm green execution.

### Slice 2: Projects Studio UI Markup & Active State (`[REQ-PROJ-010]`, `[REQ-PROJ-011]`)
- [x] Task 2.1: Update `src/web/templates/index.html` to add active project header, two-pane workspace layout container, directory explorer container, and viewer container.
- [x] Task 2.2: Update `src/web/static/modules/studios/projects.js` to change "Open" to "Set as Active" and render `[Active Project]` green badge.

### Slice 3: Directory Tree & Artifact Viewer (`[REQ-PROJ-012]`, `[REQ-PROJ-013]`)
- [x] Task 3.1: Implement directory tree rendering with folder expand/collapse and file selection in `projects.js`.
- [x] Task 3.2: Implement category quick filters (`All`, `Cards`, `Specs`, `Steering`, `ADRs`) in `projects.js`.
- [x] Task 3.3: Implement artifact viewer with markdown parsing via `marked` and code view with line numbers in `projects.js`.
- [x] Task 3.4: Add path copy button and manual tree refresh button.

### Slice 4: Verification, RTM & DoD
- [x] Task 4.1: Run pytest integration tests and frontend smoke checks.
- [x] Task 4.2: Update `docs/rtm.json` with `REQ-PROJ-010`..`REQ-PROJ-014` and run `verify_rtm.py`.
- [x] Task 4.3: Run `ruff check .`.
- [x] Task 4.4: Update `CHANGELOG.md` under `[Unreleased]`.
- [x] Task 4.5: Update CARD-191 status to `In Review`.
