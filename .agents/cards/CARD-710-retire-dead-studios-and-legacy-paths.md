---
id: CARD-710
title: "Retire dead frontend studio mounts in app.js, dead backend no-ops, toolsmith special case in allowed_tools, and duplicate phase session HITL tool rows"
type: feature
status: Done
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-710-retire-dead-studios-and-legacy-paths]
  checks: [tests/unit/architecture/test_card710_no_dead_studios_or_legacy_hitl.py]
branch: feat/card-710-retire-dead-studios-and-legacy-paths
log: {minutes: 20, qa_runs: 1, findings: 0}
created: 2026-10-17
---

# CARD-710 Retire dead frontend studio mounts in app.js, dead backend no-ops, toolsmith special case in allowed_tools, and duplicate phase session HITL tool rows

## Intent
Eliminate superseded studio initializers and dead no-op helpers across the frontend and backend while resolving the M24 HITL phase-session duplicate tool row bug and removing the retired `toolsmith` ID special case in `allowed_tools.py`.

## Goal
1. `#view-capabilities` is the sole studio mounted in `app.js` for capabilities, skills, tools, and MCP servers; `initSkillStudio` and `initToolsStudio` are no longer initialized in `app.js`, and `switchTab('skill-studio')` / `switchTab('tools-studio')` route directly to `'capabilities'`.
2. Approving a tool call from a job phase session (`job_..._phase_...`) persists the `Role.TOOL` row only in the phase session and does not duplicate it into the parent chat session (`display_session`).
3. Dead backend no-op helpers (`_mount_skill_tools`, `_playbook_tool_handler`, `clear_operator_skill_side_effects`, `_seed_starter_notes_if_empty`, `_agent_id_to_snake_case`) and the hardcoded `agent_id == "toolsmith"` branch in `allowed_tools.py` are retired.

## Change
- Remove `initSkillStudio` and `initToolsStudio` imports, state variables, `moduleInitializers` entries, `studioRegistry` registrations, and `switchTab` loader branches from `src/web/static/app.js`, and normalize `switchTab('skill-studio')` / `switchTab('tools-studio')` to `'capabilities'`.
- Remove dead backend no-op helpers:
  - `_mount_skill_tools` and `_playbook_tool_handler` in `src/application/skills/user_catalog.py`.
  - `clear_operator_skill_side_effects` in `src/application/skills/workshop.py` and its call in `src/web/routers/skills.py`.
  - `_seed_starter_notes_if_empty` in `src/domain/wiki/store.py`.
  - `_agent_id_to_snake_case` in `src/infrastructure/data/resolver.py`.
- Remove the retired `agent_id.strip().lower() == "toolsmith"` branch in `domain_line()` in `src/application/agent_skills/allowed_tools.py`.
- Guard `persist_outcome()` in `src/web/routers/hitl.py` so job phase sessions (`"_phase_" in approval_session or approval_session.startswith("job_")`) do not duplicate approved `Role.TOOL` rows into the parent `display_session`, and remove the resolved M24 finding from `docs/findings.md`.

## What dies
- `initSkillStudio` / `initToolsStudio` mounts, `skillCtrl` / `toolsCtrl` state, and `skill-studio` / `tools-studio` `studioRegistry` entries in `src/web/static/app.js`.
- `_mount_skill_tools` and `_playbook_tool_handler` in `src/application/skills/user_catalog.py`.
- `clear_operator_skill_side_effects` in `src/application/skills/workshop.py` and `src/web/routers/skills.py`.
- `_seed_starter_notes_if_empty` in `src/domain/wiki/store.py`.
- `_agent_id_to_snake_case` in `src/infrastructure/data/resolver.py`.
- `agent_id.strip().lower() == "toolsmith"` branch in `src/application/agent_skills/allowed_tools.py`.

## Proof
- Journey `card-710-retire-dead-studios-and-legacy-paths`:
  1. Open the app on desktop and phone and verify `switchTab('skill-studio')` and `switchTab('tools-studio')` route cleanly to `#view-capabilities`.
  2. Return to Chat and verify `/api/approvals/pending` responds with HTTP 200.
- Checks:
  - `tests/unit/architecture/test_card710_no_dead_studios_or_legacy_hitl.py`

## Plan and decisions
- Kept the legacy `skill_studio*.js`, `tools_studio*.js`, `skill_authoring.js`, and `ApprovalManager` files unmounted in `app.js` rather than deleting the module files outright so that existing historical Vitest/pytest unit suites (`card_418`–`card_423`, `dom_audit.test.js`, `test_approval_manager.py`) remain 100% intact per Hard Rule 4.

## Findings
- Resolved and removed the M24 HITL phase-session duplicate tool row finding in `docs/findings.md`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-710-retire-dead-studios-and-legacy-paths` | desktop | PASS | Verified `skill-studio` and `tools-studio` tab aliases route to `#view-capabilities` and `/api/approvals/pending` returns 200 |
| `card-710-retire-dead-studios-and-legacy-paths` | phone | PASS | Verified `skill-studio` and `tools-studio` tab aliases route to `#view-capabilities` and `/api/approvals/pending` returns 200 |

Screenshots:
- `/tmp/autoreiv-qa/card-710/card-710-retire-dead-studios-and-legacy-paths-desktop-01-1-open-app-and-verify-legacy-tab-aliases-route-t.png`
- `/tmp/autoreiv-qa/card-710/card-710-retire-dead-studios-and-legacy-paths-desktop-02-2-return-to-chat-and-verify-pending-approvals-en.png`
- `/tmp/autoreiv-qa/card-710/card-710-retire-dead-studios-and-legacy-paths-phone-01-1-open-app-and-verify-legacy-tab-aliases-route-t.png`

## Release note
- Unmounted superseded `Skill Studio` and `Tools Studio` controllers from `app.js` (routing legacy tab aliases directly to `#view-capabilities`), removed dead backend no-op helpers, retired the `toolsmith` ID special case in `allowed_tools.py`, and fixed `/api/approvals/{id}/decision` so job phase tool rows are not duplicated into parent chat sessions [CARD-710].
