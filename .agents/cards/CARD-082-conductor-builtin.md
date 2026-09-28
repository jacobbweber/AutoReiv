# [CARD-082] Conductor Builtin

> **Status**: Done
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/conductor-builtin/`
> **Labels**: `type:feature`, `area:agents`
> **review_rounds**: 0
> **max_review_rounds**: 3
> **return_reason**: 
> **github_issue**: 

---
## 1. Why / Intent
Jacob talks only to Conductor. Conductor writes cards and specs, hands off one Ready card at a time, and asks Jacob when review is maxed or the idea is still Discuss. It does not code.

## 2. What to Build
- Builtin `id=conductor`, name Conductor. Tone friendly/concise. Purpose general.
- Allowlist ONLY: list_cards, read_card, write_card, set_card_status, read_spec, write_spec, read_steering, list_project_dir, read_project_file, handoff_to_agent, lookup_agents.
- NO execute_code, cli_exec, write_project_file, git write.
- Pin: write_card, handoff_to_agent.
- lookup aliases: product, plan, scrum, conductor.
- Chat / Forge / lookup_agents list it without a Forge save.

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-SDLC-030]`: Conductor allowlist is exactly those 11 tools. execute_code and cli_exec are denied.
- [x] `[REQ-SDLC-034]`: lookup aliases product, plan, scrum, conductor resolve to Conductor. Chat/Forge lists it.
- [x] Automated tests green via pytest on touched Python.
- [x] Zero lint errors via ruff check on touched Python.

## 4. Constraints & Honor Flags
- Do not give Conductor execute_code, cli_exec, or write_project_file.
- Do not invent a second HITL or handoff engine.
- Do not push. Stay on `qa`.
