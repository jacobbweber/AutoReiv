# Requirements

- REQ-SDLC-050: Setting `projects_root` is a filesystem path. GET/PUT `/api/settings/projects_root`. Default empty with a placeholder. List and create projects only under that root (jail).
- REQ-SDLC-051: GET/POST `/api/projects`, DELETE `/api/projects/{slug}?confirm=true`. Delete without confirm is denied. Studio is a sidebar tab separate from Wiki.
- REQ-SDLC-052: PUT/GET `/api/projects/selected`. When card/file tools omit `project_root`, they use the selected project path if set, else the AutoReiv checkout.
