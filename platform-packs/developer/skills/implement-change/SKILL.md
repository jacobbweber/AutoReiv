---
name: Implement a Change
description: "Make small, focused edits in the project's own style, keep docs in step, and never add a dependency without asking."
version: 1.0.0
tier: platform
requires_tools:
  - read_project_file
  - write_project_file
  - patch_project_file
  - list_project_dir
  - search_project
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: "Only files inside the active project changed, none under Don't touch, no scratch files remain, and the fast check passes."
---

# Implement a Change

Make small, focused edits in the project's own style, keep docs in step, and never add a dependency without asking.

Project facts (commands, branches, rules) come from the project's AGENTS.md, never from this skill.
## Steps
1. Re-read the file right before editing it.
2. Prefer `patch_project_file` (exact old text -> new text). Use `write_project_file` only for new files or full rewrites of small files.
3. Match the surrounding style: naming, error handling, imports, formatting. Follow AGENTS.md `## Rules`.
4. After each meaningful edit run the fast check (skill run-checks) instead of piling up changes.
5. If behaviour changes for users, update the README or CHANGELOG the project already keeps.

## Rules
- Edit only inside the active project, and never paths listed under AGENTS.md `## Don't touch`.
- No throwaway scripts in the project; verification runs through the AGENTS.md checks (`run_project_checks`).
- New dependency, migration, or deleting data: ask first.
- Keep secrets out of code and commits.

## Done when
Only files inside the active project changed, none under Don't touch, no scratch files remain, and the fast check passes.
