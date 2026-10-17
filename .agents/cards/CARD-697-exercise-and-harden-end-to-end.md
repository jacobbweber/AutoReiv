---
id: CARD-697
title: "Exercise and harden end-to-end self-development on AutoReiv"
type: feature
status: In Review
priority: P2
milestone: M29
needs_decision: none
proof:
  journeys: [card-697-exercise-and-harden-end-to-end]
  checks: [tests/unit/skills/test_card697_self_development_skills.py]
branch: feat/card-697-exercise-and-harden-end-to-end
log: {minutes: 32, qa_runs: 2, findings: 2}
created: 2026-10-16
---

# CARD-697 Exercise and harden end-to-end self-development on AutoReiv

## Intent
Exercise `AutoReiv`'s consolidated `project-cards` and `software-development` Agora skills end-to-end inside the running app, review any friction or gaps encountered during the self-development workflow, and harden the skills and tools based on those findings.

## Goal
`AutoReiv` can manage projects (`create_project`, `detect_drift`, `align_project`), pick and plan a card via `project-cards`, implement and test a change via `software-development` (`run_project_checks`, `run_journey`), and move a card to `In Review` smoothly from Chat and Projects Studio.

## Change
- Register `detect_drift` (read) and `align_project` (write) alongside `create_project` in `ProjectsService.register_tools` (`src/application/sdlc/projects_service.py`), classify them in `src/application/kernel/tool_access.py`, `src/application/kernel/hitl_engine.py`, and `src/application/safety/tool_policy_gate.py`, and bind `create_project`, `detect_drift`, and `align_project` into `platform/skills/project-cards/SKILL.md` (`docs/findings.md` M25).
- Harden on-demand SDLC skill mounting for `AutoReiv`:
  1. In `tool_not_offered_error` (`src/application/kernel/tool_registry.py`), when the model calls a tool granted by one of its ticked skills that is not yet mounted in the session, tell the model which skill owns the tool and to call `skill_view(skill_id='<skill>')` first.
  2. Clarify `git_create_branch(name=...)` and `git_commit(subject=..., paths=[...])` parameter conventions in `platform/skills/software-development/SKILL.md`, and ensure `ProjectsService.create_project` sets a repo-local fallback git author identity if none is configured globally.
  3. Fix `ProjectsService.browse_folders` (`src/application/sdlc/projects_service.py`) to return `success=True` with empty `folders` when `projects_root` is unset (matching `list_projects()`), eliminating the spurious `projects_root is not set` error toast when opening `#view-projects`.
- Wire `MCPEngineeringTools` in `src/infrastructure/agents/registry.py` and `src/application/skills/mcp_engineering_tools.py` to `projects_service.selected_or_refuse` (`docs/findings.md` M25).
- Remove resolved M25 self-development items from `docs/findings.md` and log out-of-area UI findings under M29.

## What dies
- Unbound project management tools (`create_project`, `detect_drift`, `align_project` finding in `docs/findings.md`), `MCPEngineeringTools` `resolve_root` fallback (`docs/findings.md` M25), unmounted on-demand SDLC tool refusal dead-ends, and the spurious `projects_root is not set` error toast in `ProjectsService.browse_folders`.

## Proof
- Journey `card-697-exercise-and-harden-end-to-end`:
  1. In Chat, have `AutoReiv` load `project-cards` and `software-development` via `skill_view`, inspect project cards/drift, edit a target file and test in an isolated project workspace, run `run_project_checks`, and move the card to `In Review`.
  2. Verify the updated card (`status: In Review` and `## Evidence`) and aligned project state in `#view-projects` on desktop and phone.
- Checks:
  - `tests/unit/skills/test_card697_self_development_skills.py`

## Plan and decisions
- Technical only (`needs_decision: none`).

## Findings
- **Fixed in-area (`src/application/sdlc/projects_service.py`, `platform/skills/software-development/SKILL.md`)**:
  - `ProjectsService.browse_folders` returned `{"success": False, "error": "projects_root is not set"}` when `projects_root` was unset (unlike `list_projects()`), triggering a red `[role="alert"]` error toast on opening `#view-projects`. Fixed to return `success=True` with `folders=[]` when `projects_root` is empty.
  - `ProjectsService.create_project` initialized a git repository without a repo-local fallback `user.name` / `user.email`, causing `git_commit` to fail in environments without global git user config. Added fallback repo-local `user.name` / `user.email` when unset.
  - Updated `platform/skills/software-development/SKILL.md` to specify `git_create_branch(name="feat/card-N-slug")` and `git_commit(subject="feat(scope): summary", paths=["path/to/file"])`.
- **Logged in `docs/findings.md` (M29)**:
  - `#chatActiveProjectPill` (`src/web/static/modules/studios/chat.js:385`) and `#projectsPairDeveloperBtn` (`src/web/static/modules/studios/projects.js:782`) still hardcode `selectedAgentId === 'developer'` after `developer` was folded into `autoreiv` (`CARD-682`), hiding the active-project pill for `autoreiv` (both files are >800 lines and require module extraction when touched).

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-697-exercise-and-harden-end-to-end` | desktop | PASS | `AutoReiv` mounted `project-cards` + `software-development`, aligned `CHANGELOG.md`, branched `feat/card-1-add-returns-sum`, patched `calc.js`, ran `run_project_checks`, moved `CARD-1` to `In Review` with `## Evidence`, and verified in `#view-projects`. |
| `card-697-exercise-and-harden-end-to-end` | phone | PASS | Same 4 steps passed on mobile viewport (`390x844`), including `#view-projects` card viewer with `In Review` + `## Evidence`. |
| `preflight.py --fast --base qa` | fast tier | GREEN (26 s) | `ruff` PASS, `eslint` PASS, `pytest guard` 229 passed, `pytest changed` 16 passed, `pytest mapped` 905 passed, `vitest` 1121 passed. |

Screenshots:
- `/tmp/autoreiv-qa/card-697/card-697-exercise-and-harden-end-to-end-desktop-03-autoreiv-mounts-project-cards-software-developme.png`
- `/tmp/autoreiv-qa/card-697/card-697-exercise-and-harden-end-to-end-desktop-04-projects-studio-shows-aligned-state-drift-banner.png`
- `/tmp/autoreiv-qa/card-697/card-697-exercise-and-harden-end-to-end-phone-04-projects-studio-shows-aligned-state-drift-banner.png`

## Release note
- Bound project alignment tools into `project-cards` and hardened `AutoReiv`'s end-to-end self-development workflow across Chat and Projects Studio [CARD-697].
