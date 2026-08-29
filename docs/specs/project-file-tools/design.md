# Design

Reuse `jail_join` / `resolve_project_root`. One skill. No studio.

## Action to route to function

1. Tool `list_project_dir` -> `ProjectFileSkill.list_project_dir` -> jail `path` under `project_root` -> list names (files + dirs), no recursion dump of the whole tree unless `recursive` is false by default (one directory).
2. `read_project_file` -> jail -> read UTF-8 text (deny if missing or not a file). Cap huge files with an excerpt + truncated flag (same spirit as `read_steering`).
3. `write_project_file` -> jail -> create parents -> write UTF-8 (HITL park via existing high-risk list).
4. Any `..` part or resolved path outside root -> `{success: false, error: Path escapes project_root}`.

## Out of this slice

Projects studio, git tools, agent allowlist grants (later cards).
