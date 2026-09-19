# Technical Design: Projects Studio Web Workspace with Active State and Directory Tree Artifact Viewer

## Architectural Context (C4 Component)

The Projects Studio Web Workspace spans three tiers:
1. **Frontend Studio Module** (`src/web/static/modules/studios/projects.js` & `src/web/templates/index.html`):
   - Renders the active project selector and `[Active Project]` badge (`REQ-PROJ-010`).
   - Manages a two-pane responsive workspace container (`REQ-PROJ-011`).
   - Renders a directory tree with folder toggles, quick filters, and item icons (`REQ-PROJ-012`).
   - Renders file contents via `marked` or monospace `<pre><code>` (`REQ-PROJ-013`).
2. **Web Router** (`src/web/routers/projects.py`):
   - Exposes `GET /api/projects/files/list` and `GET /api/projects/files/read` (`REQ-PROJ-014`).
3. **Domain Layer & Security Jail** (`src/application/sdlc/projects_service.py` & `src/application/skills/project_file_tools.py`):
   - Resolves active project root via `ProjectsService.resolve_root()`.
   - Clamps paths with `jail_join()`.
   - Filters noise directories (`.git`, `__pycache__`, `node_modules`, `.venv`).

## API Contracts

### `GET /api/projects/files/list`
- **Query Params**:
  - `path`: string (default `.` or empty)
  - `category`: optional string (`all`, `cards`, `specs`, `steering`, `adr`)
- **Response**:
  ```json
  {
    "success": true,
    "project_root": "D:\\Projects\\Active\\demo",
    "path": ".",
    "category": "all",
    "entries": [
      {
        "name": ".agents",
        "path": ".agents",
        "type": "dir"
      },
      {
        "name": "README.md",
        "path": "README.md",
        "type": "file",
        "ext": ".md"
      }
    ]
  }
  ```

### `GET /api/projects/files/read`
- **Query Params**:
  - `path`: string (required)
- **Response**:
  ```json
  {
    "success": true,
    "project_root": "D:\\Projects\\Active\\demo",
    "path": ".agents/cards/CARD-001.md",
    "content": "# Card Content...",
    "chars": 1234,
    "is_markdown": true
  }
  ```
