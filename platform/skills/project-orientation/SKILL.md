---
name: Project Orientation
description: 'Learn the active project before touching it: read AGENTS.md, map the layout, find how to run and check it, and say what is missing.'
tools:
- active_project_info
- list_project_dir
- read_project_file
- search_project
version: 1.0.0
tier: platform
safety:
  read_only: true
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The agent can state the project's purpose, code and test folders, check commands and base branch, and lists any missing AGENTS.md section.
---

# Project Orientation

Learn the active project before touching it: read AGENTS.md, map the layout, find how to run and check it, and say what is missing.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## When
First thing in any project task, and whenever the active project changes.

## Steps
1. `active_project_info`. If no project is selected, stop and ask the operator to pick one in Projects Studio.
2. Read `AGENTS.md` in full. It is the project's rules. Where it disagrees with a skill, AGENTS.md wins for that project.
3. Note `missing_sections`. If `## Checks` is missing or empty, say so and propose the exact lines (look at `pyproject.toml`, `package.json`, `Makefile`, CI files for the real commands). Never guess a command and run it.
4. Map the layout with `list_project_dir` (root, then the source and test folders). Use `search_project` to find entry points, the module a card names, and existing tests for it.
5. Read the README only as needed. Do not read the whole repo.

## Output
Three to six lines: what the project is, where the code and tests live, the check commands, the base branch, anything missing.

## Done when
The agent can state the project's purpose, code and test folders, check commands and base branch, and lists any missing AGENTS.md section.
