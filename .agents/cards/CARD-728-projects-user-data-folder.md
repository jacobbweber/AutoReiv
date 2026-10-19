---
id: CARD-728
title: "Projects live in one user-data folder"
type: feature
status: In Progress
priority: P1
milestone: M32
needs_decision: none
proof:
  journeys: [card-728-projects-user-data-folder]
  checks: [tests/unit/architecture/test_card728_projects_user_data.py, tests/integration/test_projects_api.py]
branch: feat/card-728-projects-user-data
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-18
---

# CARD-728 Projects live in one user-data folder

## Intent
In Docker, Projects Studio's `projects_root` box could only browse the container image, never host folders, and any
folder (even the running AutoReiv code in `/app`) could be made the active project. Jacob wants projects to behave like
the wiki: one user-data folder that is the same on a native install and in Docker (mounted from the host), so repos can
be cloned or dropped there and followed in VS Code on the host.

## Goal
- Projects Studio always shows the projects folder (`<data>/projects`, or `AUTOREIV_PROJECTS_DIR` when set) read-only;
  there is no path box to type into.
- Only folders inside it can be the active project; the running AutoReiv checkout can never be selected.
- A selection saved before this change that points outside the folder is ignored (re-select once).

## Change
- `src/infrastructure/data/resolver.py`: `DataDirPaths.projects_path` = env `AUTOREIV_PROJECTS_DIR`, else
  `<root>/projects` (refused inside the checkout outside `scratch/`); `ensure_layout` creates it.
- `src/application/sdlc/projects_service.py`: the projects folder comes from the resolver (constructor `projects_dir`
  for tests). `set_selected` refuses paths outside the folder or the running checkout; `get_selected` drops a stored
  selection outside it. `projects_root` setting retired.
- `src/web/routers/projects.py`: `GET/PUT /api/settings/projects_root` removed; `GET /api/projects` still returns
  `projects_root` (the folder path).
- `src/web/templates/partials/wiki_projects.html`, `src/web/static/modules/studios/projects.js`: the `projects_root`
  input and Save button become a read-only "Projects folder" line with a hint about the Docker mount.
- Journeys that set `projects_root` (card-634, card-709) use the projects folder from `GET /api/projects` instead.

## What dies
- Setting `projects_root`, `ProjectsService.get_projects_root/set_projects_root`, `PROJECTS_ROOT_KEY`,
  `ProjectsRootRequest`, `GET/PUT /api/settings/projects_root`, `#projectsRootInput`, `#projectsRootSaveBtn`,
  `rPlaceholder()` in `projects.js`.

## Proof
- Journey `card-728-projects-user-data-folder` (desktop and phone):
  1. Open Projects Studio, Projects Manager: the projects folder path shows, no `#projectsRootInput`.
  2. Create project `demo-728` from the UI: it appears in the list and on disk inside the projects folder.
  3. Set it active: the header shows it, the explorer lists its files.
  4. `PUT /api/projects/selected` with the serve's own checkout path is refused (4xx), selection unchanged.
- Checks: guard `tests/unit/architecture/test_card728_projects_user_data.py` (ADR-0067 rules 1-2), operator contract
  `tests/integration/test_projects_api.py`.

## Plan and decisions
- Decisions approved by Jacob (`build`, 2026-10-18): fixed folder, env override at deploy time only (like the wiki),
  ADR-0067. Docker mount and toolchain are CARD-731.
- Technical: keep the `projects_root` key in API responses as the folder path to keep the UI and journeys simple.

## Findings

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
Changed: Projects now live in one user-data folder (`<data>/projects`, or `AUTOREIV_PROJECTS_DIR`), the same on native
installs and Docker; the `projects_root` setting is gone and the running AutoReiv checkout can no longer be selected
(CARD-728).
