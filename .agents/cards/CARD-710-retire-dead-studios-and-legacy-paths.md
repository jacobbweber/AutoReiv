---
id: CARD-710
title: "Retire dead frontend studios (skill_studio, tools_studio, skill_authoring), legacy /api/hitl ApprovalManager, and remaining architect/developer/toolsmith special cases"
type: feature
status: Ready
priority: P2
milestone: M31
needs_decision: none
proof:
  journeys: [card-710-retire-dead-studios-and-legacy-paths]
  checks: [tests/unit/architecture/test_card710_no_dead_studios_or_legacy_hitl.py]
branch: feat/card-710-retire-dead-studios-and-legacy-paths
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-17
---

# CARD-710 Retire dead frontend studios (skill_studio, tools_studio, skill_authoring), legacy /api/hitl ApprovalManager, and remaining architect/developer/toolsmith special cases

## Intent
Eliminate ~3,500 lines of superseded dead UI views, controllers, and legacy backend side paths that remain mounted after Capabilities Studio (`#view-capabilities`, `CARD-690`) and the Three-Agent Roster (`CARD-693`) shipped.

## Goal
1. `#view-capabilities` is the sole studio mounted in `index.html` and `app.js` for capabilities, skills, tools, and MCP servers; `#view-skill-studio`, `#view-tools-studio`, `skill_studio*.js`, `tools_studio*.js`, and `skill_authoring.js` are deleted.
2. `HITLApprovalEngine` (`/api/approvals/*`) is the single approval system; the disconnected in-memory `ApprovalManager` and `/api/hitl/*` endpoints are retired.
3. Hardcoded `agent.id` checks for retired agents (`architect`, `developer`, `toolsmith`) in `allowed_tools.py`, `agent_kernel.py`, `job_phase_orchestrator.py`, and `card_tools.py` are replaced with capability/skill-based checks or retired.

## Change
- Remove `#view-skill-studio` and `#view-tools-studio` markup (~385 lines) from `src/web/templates/index.html`.
- Delete `src/web/static/modules/studios/skill_studio.js`, `skill_studio_*.js`, `tools_studio.js`, `tools_studio_catalog.js`, and unimported `skill_authoring.js`, and remove their initialization and dead `switchTab` branches from `src/web/static/app.js`.
- Retire `src/application/hitl/approval_manager.py` (`ApprovalManager`) and the legacy `/api/hitl/pending` and `/api/hitl/decide` routes in `src/web/routers/hitl.py`, keeping the canonical SQLite-backed `HITLApprovalEngine` (`/api/approvals/*`).
- Remove dead backend no-ops (`_mount_skill_tools` / `_playbook_tool_handler` in `user_catalog.py`, `clear_operator_skill_side_effects` in `workshop.py`, `_seed_starter_notes_if_empty` in `wiki/store.py`, `_agent_id_to_snake_case` in `resolver.py`).
- Replace remaining hardcoded `architect` / `developer` / `toolsmith` ID branches in `allowed_tools.py`, `agent_kernel.py`, `job_phase_orchestrator.py`, and `card_tools.py`.

## What dies
- `#view-skill-studio` and `#view-tools-studio` in `src/web/templates/index.html`.
- `src/web/static/modules/studios/skill_studio.js`, `skill_studio_cards.js`, `skill_studio_ create_modal.js`, `skill_studio_ try_it.js`, `tools_studio.js`, `tools_studio_catalog.js`, `skill_authoring.js`.
- `src/application/hitl/approval_manager.py` and `/api/hitl/*` routes in `src/web/routers/hitl.py`.
- Dead helpers in `user_catalog.py`, `workshop.py`, `wiki/store.py`, and `resolver.py`.

## Proof
- Journey `card-710-retire-dead-studios-and-legacy-paths`:
  1. Navigate across Capabilities Studio (`#view-capabilities`) and Chat on desktop and phone, verifying legacy tab aliases (`skill-studio`, `tools-studio`) route cleanly to `#view-capabilities` and no dead `#view-skill-studio` / `#view-tools-studio` DOM exists.
- Checks:
  - `tests/unit/architecture/test_card710_no_dead_studios_or_legacy_hitl.py`

## Plan and decisions
- Phase 2 subtractive cleanup following Phase 1 bug fixes.

## Findings
- Resolves the M24 `/api/hitl/decide` finding in `docs/findings.md`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-710\...`

## Release note
- Removed superseded `skill_studio`, `tools_studio`, and `skill_authoring` frontend modules and DOM views, retired the legacy in-memory `ApprovalManager` (`/api/hitl/*`), and cleaned up remaining `architect`/`developer`/`toolsmith` special cases [CARD-710].
