---
id: CARD-739
title: "Dogfood multi-turn project development and Tutor study flow end-to-end"
type: feature
status: Done
priority: P2
milestone: M33
needs_decision: none
proof:
  journeys: [card-739-dogfood-multi-turn-project-development-and]
  checks:
    - tests/integration/test_card739_project_and_tutor_dogfood.py
branch: feat/card-739-dogfood-multi-turn-project-development-and
log: {minutes: 25, qa_runs: 2, findings: 0}
created: 2026-10-20
completed: 2026-10-20
---

# CARD-739 Dogfood multi-turn project development and Tutor study flow end-to-end

## Intent
Exercise `AutoReiv` on a real multi-turn software project loop inside `<data>/projects` (`repo-onboarding` -> `project-cards` -> `software-development` with `cli_exec` and `run_project_checks` -> `In Review`) alongside `Tutor` on a multi-turn study flow (`start-resume-topic` -> `socratic-tutoring` progressive reference -> `quiz-turn` / `flashcard-turn` -> `progress-summary`), and fix any friction or edge cases uncovered during the end-to-end run.

## Goal
- Operator can create/select a project in **Projects Studio**, have `AutoReiv` onboard the repo, create a card, branch, edit code, run checks (`run_project_checks` / remembered `cli_exec`), and transition the card to `In Review` in one multi-turn session.
- Operator can switch to `Tutor`, open a study topic, use progressive reference guidance, complete a graded quiz/flashcard turn into `education_mastery`, and inspect trustable progress in one multi-turn session without UI or tool-loop friction.

## Change
- `src/application/sdlc/projects_service.py`: `create_project` now records an initial empty root commit on `main` (`git commit --allow-empty -m "chore(repo): initialize repository"`) while keeping the working tree completely empty (`CARD-729`), and accepts `select: bool = True` (matching `git_clone`) so newly created projects become active immediately and have a valid `main` `HEAD` for `git_create_branch` and `review_card`.
- `src/application/skills/git_tools.py`: `git_create_branch` initializes an empty root commit on the initial branch when called on an externally initialized git repository with an unborn `HEAD`.
- `src/application/skills/card_tools.py`: `set_card_status` allows `actor == "autoreiv"` to transition a `Proposed` card (the default when `write_card` is called without an explicit `status:` field) directly to `In Progress` or `In Review` (`Proposed -> Ready -> In Progress [-> In Review]`).
- `src/application/skills/project_dev_tools.py` & `src/application/sdlc/check_record.py`: `run_project_checks` runs with `PYTHONDONTWRITEBYTECODE=1` and `git_dirty_paths` ignores generated tool cache directories (`__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`) so running checks in a fresh repo without a `.gitignore` never dirties the tree or blocks `In Review`.
- `src/application/education/progress_summary.py`, `src/application/skills/education_tool_schemas.py`, `src/application/safety/tool_policy_gate.py`, & `src/application/skills/session_skills.py`: added `topic_matches(row_topic, query_topic)` to normalize slug vs title-case topics (`"distributed-consensus"` vs `"Distributed Consensus"`) in `build_progress_summary` and `education_progress_mastery`, and included `socratic-tutoring` in `_EDUCATION_SKILL_MARKERS` / `session_skills.py`.
- `tests/integration/test_card739_project_and_tutor_dogfood.py`: integration contract covering both the multi-step project SDLC lifecycle and Tutor study progression.
- `tests/e2e/journeys/card-739-dogfood-multi-turn-project-development-and.mjs`: live Playwright journey exercising both flows on desktop and phone.

## What dies
- Nothing.

## Proof
- Journey `card-739-dogfood-multi-turn-project-development-and`:
  1. Creates a git project via `POST /api/projects`, verifies auto-selection and initialized `main` `HEAD` commit with zero starter template files, exercises branch + check + `CARD-1` `In Review`, and inspects `CARD-1` in Projects Studio (`#view-projects`).
  2. Exercises Tutor course start (`topic_id="distributed-consensus"`), progressive reference loading (`socratic-tutoring`), binary quiz grading (`topic="Distributed Consensus"`), and verifies `GET /api/education/progress` reports `100%` mastery across slug vs title-case topic labels.
  3. Verifies `#agentSelect` in `#view-chat` switches between `AutoReiv` and `Tutor` with zero horizontal overflow on desktop and phone.
- Checks:
  - `tests/integration/test_card739_project_and_tutor_dogfood.py`

## Plan and decisions
- None (`needs_decision: none`).

## Findings
- Findings (fixed):
  1. `create_project` left `main` as an unborn branch without a `HEAD` commit and did not auto-select the created project, causing immediate `git_create_branch` calls to fail with `invalid reference: main`. Fixed in `src/application/sdlc/projects_service.py` and `src/application/skills/git_tools.py`.
  2. `AutoReiv` calling `write_card` without an explicit `status:` field created a `Proposed` card that rejected `set_card_status("In Progress")`. Fixed in `src/application/skills/card_tools.py`.
  3. `run_project_checks` executing Python checks in a fresh repo without `.gitignore` wrote `__pycache__/*.pyc` files that blocked `green_recorded` and `set_card_status("In Review")`. Fixed in `src/application/skills/project_dev_tools.py` and `src/application/sdlc/check_record.py`.
  4. `build_progress_summary` and `education_progress_mastery` compared `topic` with case-sensitive `==`, missing mastery rows titled `"Distributed Consensus"` when queried by course slug `"distributed-consensus"`. Fixed with `topic_matches` in `src/application/education/progress_summary.py` and `src/application/skills/education_tool_schemas.py`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-739-dogfood-multi-turn-project-development-and` | desktop | PASS | 3/3 steps pass: `POST /api/projects` auto-select + `main` `HEAD` + `CARD-1` in `#view-projects`, Tutor course + progressive reference + graded recall + `100%` topic-matched progress, `#agentSelect` in `#view-chat` |
| `card-739-dogfood-multi-turn-project-development-and` | phone | PASS | 3/3 steps pass, zero horizontal overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-739/card-739-dogfood-multi-turn-project-development-and-desktop-01-1-create-fresh-project-via-api-verify-auto-selec.png`
- `/tmp/autoreiv-qa/card-739/card-739-dogfood-multi-turn-project-development-and-desktop-03-3-switch-to-chat-view-view-chat-verify-autoreiv-.png`
- `/tmp/autoreiv-qa/card-739/card-739-dogfood-multi-turn-project-development-and-phone-01-1-create-fresh-project-via-api-verify-auto-selec.png`

## Release note
- Hardened multi-turn active-project software development (`create_project` auto-select and root commit on `main`, `Proposed -> In Progress/In Review` transitions for `AutoReiv`, bytecode-clean `run_project_checks`) and `Tutor` study progression (`socratic-tutoring` policy gate and slug-vs-title topic matching in `education_progress_summary`) (`CARD-739`).
