---
name: Spec-Driven Development
description: Turn a feature idea into a spec, a technical plan and a task list in the repo's specs folder (or specs/<feature>/ when it has none), then build task by task against the spec.
tools:
- active_project_info
- list_project_dir
- read_project_file
- search_project
- write_project_file
- patch_project_file
version: 1.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: false
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: A feature has spec.md (what and why), plan.md (how) and tasks.md (ordered, checkable tasks) before code changes, and tasks are ticked as they are done.
---

# Spec-Driven Development

Use this runbook when the operator wants to design a feature before coding it ("write a spec", "plan this feature",
"spec-driven"), or when the repo already keeps specs. Open
`skill_view(skill_id="spec-driven-development", reference="templates.md")` for the three file templates.

## Workflow

1. **Use the repo's format.** Look for an existing specs folder (`specs/`, `.specify/`, `docs/specs/`) and copy its
   layout and file names. Only when there is none, use `specs/<NNN>-<feature-slug>/` with `spec.md`, `plan.md` and
   `tasks.md` (NNN = next number). Follow `repo-onboarding` first if you have not read the repo's conventions.
2. **Specify (what and why).** Write `spec.md` with the operator: user stories, acceptance criteria that can be
   checked, and open questions marked `[NEEDS CLARIFICATION: ...]`. No technology choices here. Ask the operator to
   resolve every open question (2-3 options with your recommendation) before planning.
3. **Plan (how).** Write `plan.md`: architecture, libraries and why, data model, interfaces, how each acceptance
   criterion will be tested, and risks. Respect the repo's stack and rules; a new dependency needs the operator's OK.
4. **Tasks.** Write `tasks.md`: small ordered tasks (`- [ ] T001 ...`), tests before the code they prove, each naming
   the files it touches. Mark tasks that can run in parallel with `[P]`.
5. **Build against the spec.** Use `software-development` to do one task at a time: branch, test first, change,
   run the repo's checks, commit. Tick the task in `tasks.md` (`patch_project_file`) when its check passes. If the
   build shows the spec was wrong, update `spec.md` and `plan.md` first and tell the operator.

## Done when
- Every acceptance criterion in `spec.md` has a passing check, and every task in `tasks.md` is ticked.
