---
name: Repo Onboarding
description: Set up or adopt a project in the projects folder, find and follow the repo's own conventions (AGENTS.md, CLAUDE.md, Copilot or Cursor rules, CONTRIBUTING, build files), and add starter files only when the repo has none.
tools:
- active_project_info
- create_project
- list_project_dir
- read_project_file
- search_project
- write_project_file
- git_status
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The repo's existing instruction files are read and summarised before any starter file is written; no existing file is overwritten.
---

# Repo Onboarding

Use this runbook when the operator starts a new project, brings in a repo (cloned or copied into the projects folder),
or asks "how does this repo work?". The repo's own rules always win over AutoReiv's habits. Open
`skill_view(skill_id="repo-onboarding", reference="conventions.md")` for the file list and
`reference="starter-agents-md.md"` for the starter `AGENTS.md`.

## Workflow

1. **Find the project.** Call `active_project_info`. If no project is selected, ask the operator to select one in
   Projects Studio. To start a brand-new one, call `create_project(slug)` (an empty git repo in the projects folder),
   then ask the operator to select it.
2. **Read what is there first.** With `list_project_dir` and `read_project_file`, read every instruction file that
   exists (see `conventions.md`): `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`,
   `.cursor/rules/`, `.cursorrules`, `CONTRIBUTING.md`, `README.md`, and the build files (`package.json` scripts,
   `Makefile`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `project.godot`, CI workflows).
3. **Summarise the conventions** for the operator in a short list: language and framework, how to install, run, test
   and lint (exact commands), branch and commit style, where specs, cards, issues or ADRs live, and any "don't touch"
   rules. Say which file each fact came from.
4. **Adopt, don't replace.** Follow those conventions for all later work. If the repo tracks work in GitHub issues,
   use issues; if it has a specs folder, use `spec-driven-development` there; if it has its own card or task format,
   use it. Never rename, move or rewrite the repo's instruction files to match AutoReiv.
5. **Starter files only when missing and wanted.** If the repo has no agent instruction file, offer a starter
   `AGENTS.md` (from `starter-agents-md.md`, filled with the facts you found). Offer cards (`project-cards`) or specs
   (`spec-driven-development`) only if the operator wants that way of working. Write with `write_project_file`; it
   overwrites an existing file, so check with `list_project_dir` that the file is missing first.

## Done when
- The operator has a summary of how the repo builds, tests and is organised, with sources.
- Any starter file written was missing before and the operator agreed to it.
