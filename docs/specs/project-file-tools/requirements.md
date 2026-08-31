# Requirements

- REQ-SDLC-021: All project file paths resolve under `project_root`. Reject `..` escapes and absolute paths outside the root.
- REQ-SDLC-022: Tools `list_project_dir`, `read_project_file`, `write_project_file` are on the master registry. `write_project_file` is high-risk HITL. Optional `project_root` defaults to the AutoReiv checkout until Projects exist.
- REQ-SDLC-023: Grant later: read tools to Conductor+Review+Coding; write to Coding only. This card registers tools; it does not bloat Assistant/AutoReiv allowlists.
