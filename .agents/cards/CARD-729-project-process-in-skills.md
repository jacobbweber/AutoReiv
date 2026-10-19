---
id: CARD-729
title: "Project process lives in skills, not templates"
type: feature
status: In Review
priority: P1
milestone: M32
needs_decision: none
proof:
  journeys: [card-728-projects-user-data-folder]
  checks: [tests/unit/architecture/test_card728_projects_user_data.py, tests/unit/skills/test_card697_self_development_skills.py, tests/unit/kernel/test_card562_prompt_names_allowed_tools.py]
branch: feat/card-728-projects-user-data
log: {minutes: 240, qa_runs: 1, findings: 2}
created: 2026-10-18
---

# CARD-729 Project process lives in skills, not templates

## Intent
Projects Studio pushed AutoReiv's own engineering process onto every repo: `create_project` copied the
`templates/sdlc-project` scaffold and `detect_drift` / `align_project` flagged any repo without it as drifted, even a
GitHub repo that already has its own `AGENTS.md`, `CLAUDE.md`, Copilot or Cursor rules. Jacob wants AutoReiv to adapt
to a repo's conventions, offer starter files only when a repo has none, support spec-driven development, and be able to
run the project's real build and test commands.

## Goal
- A cloned or existing repo shows no "drift" or "Align to template" banner.
- New projects start as an empty git repo; AutoReiv writes a starter `AGENTS.md`, cards or specs only when asked or
  when the repo has none, following a skill.
- AutoReiv has skills to onboard a repo (`repo-onboarding`), do spec-driven development (`spec-driven-development`),
  and run project commands (`cli_exec` in `software-development`, approval per call).

## Change
- `src/application/sdlc/projects_service.py`: `create_project` makes an empty folder with `git init -b main`; drift,
  align and the template manifest are deleted.
- `src/web/routers/projects.py`: `GET /api/projects/drift`, `POST /api/projects/align` removed.
- `src/web/templates/partials/wiki_projects.html`, `projects.js`, `studios.css`: drift banner and Align button removed;
  Create hint says it makes an empty git repo.
- New `platform/skills/repo-onboarding/` (`SKILL.md`, `references/conventions.md`, `references/starter-agents-md.md`):
  read the repo's own instruction files and build files, adopt them; offer starter files only when none exist.
- New `platform/skills/spec-driven-development/` (`SKILL.md`, `references/templates.md`): spec, plan, tasks in the
  repo's existing specs folder, or `specs/<feature>/` when it has none.
- `platform/skills/software-development/`: adds `cli_exec`; the runbook follows the repo's own rules first and uses
  `run_project_checks` only when `AGENTS.md` has `## Checks`.
- `platform/skills/project-cards/`: drops `create_project`, `detect_drift`, `align_project`; cards are opt-in and use
  the repo's card folder; the starter card template moves into `references/card-rubric.md`.
- `platform/agents/autoreiv.md`: ticks `repo-onboarding` and `spec-driven-development`.
- `tool_policy_gate.py`, `hitl_engine.py`, `tool_access.py`, `missing_tool.py`, `distillation_service.py`: drop the
  retired tool names.
- `steering/self-development.md`, `steering/product.md`: describe the new shape.
- Dockerfile and the update sparse-checkout stop listing `templates/` (done on CARD-731).

## What dies
- `templates/sdlc-project/` (whole folder), `REQUIRED_SCAFFOLD`, `NAME_PLACEHOLDER`, `default_template_dir`,
  `load_template_manifest`, `detect_drift`, `align_project`, `resolve_root` and `default_checkout` if orphaned,
  `/api/projects/drift`, `/api/projects/align`, `#projectsDriftBanner`, `#projectsAlignBtn`,
  `#projectsDriftSummary`, `#projectsDriftMissing`, `loadDrift()`, `.proj-missing-path` CSS,
  `tests/unit/sdlc/test_projects_drift_302.py`, the drift parts of `test_card697_self_development_skills.py` and the
  card-697 journey's align steps.
- The CARD-562 rule "no shell or code runner on Developer" (Jacob decision 3, ADR-0067 rule 4): its guard is rewritten
  to "`cli_exec` is offered only with approval and the dangerous-command filter".

## Proof
- Journey `card-728-projects-user-data-folder` step: a project with its own `CLAUDE.md` and no `AGENTS.md` shows no
  drift banner and no Align button.
- Checks: guard `tests/unit/architecture/test_card728_projects_user_data.py` (ADR-0067 rule 3-4: no drift/align tools
  or endpoints, no `templates/sdlc-project`), 
  replaced by the guard's `test_create_project_is_an_empty_git_repo` and
  `test_process_skills_ship_and_software_development_offers_cli_exec`, `test_card697_self_development_skills.py`
  (repo-onboarding flow) and `test_card562_prompt_names_allowed_tools.py` (`cli_exec` needs approval).

## Plan and decisions
- Decisions approved by Jacob (`build`, 2026-10-18): process in skills, tools keep safety only; general command runner
  with approval (ADR-0067).
- Technical: reuse the existing `cli_exec` (already runs in the selected project, needs confirmation, dangerous filter)
  instead of a new runner (one code path). Per-call approval stays; "remember approved commands" is a finding.
- Shares a branch with CARD-728 because both change `projects_service.py`, `projects.js` and the Projects partial.

## Findings
- (fixed) `live-journeys` skill split out of `software-development` because the skill linter caps a skill at 15 tools.
- (fixed) Guards that encoded the CARD-562 "no shell" rule (`test_builtin_profiles`, `test_autoreiv_alignment_407`,
  `test_card562_prompt_names_allowed_tools`, `test_card562_developer_skills`, `test_card_181`, `test_sysadmin_network_info`)
  now assert the ADR-0067 rule: `cli_exec` only from `software-development`, gate verdict REQUIRE_CONFIRM, `execute_code`
  still blocked. `test_card578` tool count 33 -> 27 (journey tools and create/drift/align moved out, `cli_exec` in).
- (logged) `cli_exec` asks on every call; "remember approved commands for this project" would cut approval noise.
- (logged) AGENTS.md product lock still says the model sees at most 15 tools per turn; ADR-0064 removed the per-turn cap.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-728-projects-user-data-folder | desktop | PASS | 4/4 steps: folder shown, UI create = empty git repo, CLAUDE.md project active with no drift/Align, outside paths 400 |
| card-728-projects-user-data-folder | phone | PASS | 4/4 steps |
| card-634-projects-journey-runs (updated) | desktop, phone | PASS | no projects_root setup needed |
| card-709-web-and-ui-wiring-fixes (updated) | desktop, phone | FAIL (step 3 only) | step 2 (create + select in the projects folder, active project pill) PASS; step 3 (Settings model discovery) fails before this card: it calls `window.__autoreivSwitchTab`, which no longer exists in `src/web/static` (finding) |
| preflight --fast --base qa | - | GREEN | ruff, eslint, guard 307, changed 131, mapped 479, vitest 1139 |
| pytest tests/unit + tests/integration | - | PASS | 3060 passed, 12 skipped |

Screenshots:
- /tmp/autoreiv-qa/card-728/card-728-projects-user-data-folder-desktop-01-projects-manager-shows-the-fixed-projects-folder.png
- /tmp/autoreiv-qa/card-728/card-728-projects-user-data-folder-desktop-03-a-project-with-its-own-claude-md-becomes-active-.png
- /tmp/autoreiv-qa/card-728/card-728-projects-user-data-folder-phone-02-create-a-project-from-the-ui-and-see-an-empty-gi.png

## Release note
Changed: Projects Studio no longer pushes AutoReiv's template onto repos (drift and Align removed, new projects are an
empty git repo); new `repo-onboarding` and `spec-driven-development` skills adopt a repo's own conventions, and
`software-development` can run project commands with approval (CARD-729).
