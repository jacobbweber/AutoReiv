# Design

`ProjectsService.create_project` copies the template with shutil.copytree. Studio POST and the tool share that method.

## Action to route to function

1. Studio Create or tool `create_project` -> `ProjectsService.create_project` -> jail slug -> copytree `templates/sdlc-project/` -> `{projects_root}/{slug}/`.
2. Missing template falls back to mkdir plus a note. Escape slugs fail.

Conductor allowlist stays 11. The tool is in the catalog for Forge.

## Out of this slice

Git tools. GitHub issues. Language-specific scaffolds.
