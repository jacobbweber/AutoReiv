# Design

Separate store and view from wiki. Reuse jail_join.

## Action to route to function

1. Settings PUT `/api/settings/projects_root` -> `ProjectsService.set_projects_root` -> SQLite setting.
2. GET `/api/projects` -> scan immediate child directories of `projects_root`.
3. POST `/api/projects` `{slug}` -> jail slug under root -> mkdir (template copy is CARD-086).
4. DELETE `/api/projects/{slug}?confirm=true` -> jail -> rmtree. Missing confirm -> 400.
5. PUT `/api/projects/selected` -> store selected path. CardSkill/ProjectFileSkill `root_resolver` reads it.
6. Studio tab `projects` lists, creates, selects, deletes (window confirm then DELETE confirm=true).

## Out of this slice

SDD template copy (CARD-086). Git. GitHub issues.
