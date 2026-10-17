---
id: CARD-691
title: "Hands-free Agora skill authoring and auto-discovery for AutoReiv"
type: feature
status: Done
priority: P1
milestone: M27
needs_decision: none
proof:
  journeys: [card-691-hands-free-agora-skill-authoring-and]
  checks: [tests/unit/architecture/test_card691_autoreiv_agora_handsfree.py]
branch: feat/card-691-692-agora-adoption-and-consolidation
log: {minutes: 35, qa_runs: 2, findings: 1}
created: 2026-10-16
completed: 2026-10-16
---

# CARD-691 Hands-free Agora skill authoring and auto-discovery for AutoReiv

## Intent
Switch `AutoReiv` to hands-free Agora skill authoring and automatic discovery of user skill folders (`<data>/skills/<id>/`) so `AutoReiv` can author `SKILL.md`, `references/*.md`, and `tools/*.py` directly in conversation, auto-discover any user skill folder without manual ticking in Agent Studio, and mount its tools on demand via `skill_view("<id>")` while preserving `Developer` (`coding`) and `Tutor` (`socratic-tutoring`) specialist domain boundaries.

## Goal
- `AutoReiv` (`platform/agents/autoreiv.md`) declares `user:*` in its `skills:` list alongside its pinned platform skills.
- `AUTO_USER_SKILL_WILDCARD = "user:*"` in `src/application/agent_skills/allowed_tools.py`, `src/application/skills/session_skills.py`, and `src/application/skills/user_catalog.py` automatically expands to all non-hidden user skill folders in `<data>/skills/<id>/` (without pulling in specialist-only shipped skills like `coding`, `socratic-tutoring`, or `coordination`), includes them in the progressive skill index, and mounts their tools on demand when opened with `skill_view("<id>")` or authored with `write_skill_file`.
- `platform/skills/agent-authoring/SKILL.md` binds `write_skill_file`, `skill_view`, and `list_available_skills_and_tools` and instructs `AutoReiv` to write Agora skill folders (`SKILL.md`, `references/*.md`, `tools/*.py`) directly for user capabilities, auto-enabling pure `read_only` tools immediately and directing outside-access tools to **Capabilities** (`#view-capabilities`) for one-click enablement.

## Change
- `src/application/agent_skills/allowed_tools.py`:
  - Add `AUTO_USER_SKILL_WILDCARD = "user:*"`, update `has_auto_skill_wildcard`, `pinned_skills`, and `ticked_skills` so `user:*` expands to all non-hidden user-created skill folders (`_store().skills.user_ids()`) while keeping pinned shipped skills active on every turn and skipping single-agent legacy `attach_tool_to_skill` skills that belong exclusively to another specialist agent.
- `src/application/skills/session_skills.py` & `src/application/skills/user_catalog.py`:
  - Update `render_skill_index`, `resolve_turn_active_tools`, and `UserSkillCatalog._allowed_skill_ids_for_current_agent` so `user:*` includes all user skill folders in the progressive skill index, authorizes `skill_view("<id>")`, and mounts their tools on demand after `skill_view` or `write_skill_file` in the session.
- `platform/agents/autoreiv.md`:
  - Add `user:*` to `skills:` and update the `[TOOL USAGE RULES]` and `[DOMAIN BOUNDARIES & REFUSALS]` guidance for inline Agora skill/tool authoring and **Capabilities** studio review.
- `platform/skills/agent-authoring/SKILL.md`:
  - Add `write_skill_file`, `skill_view`, and `list_available_skills_and_tools` to `tools:` and update the runbook protocol to write Agora skill folders inline.

## What dies
- Legacy `agent-authoring` runbook rule that forbade inline skill/tool creation ("You do not build tools here") and forced a manual detour to Skill Studio or Toolsmith for routine user skills and pure helper tools.

## Proof
- Journey `card-691-hands-free-agora-skill-authoring-and`:
  1. Seed an Agora skill folder (`<data>/skills/handsfree-math/` with `SKILL.md` and `tools/triple_plus_one.py`) without editing `AutoReiv` in Agent Studio and verify `AutoReiv` automatically discovers `handsfree-math` and `triple_plus_one` via `user:*`.
  2. Open `AutoReiv` in Chat, ask it to open `handsfree-math` with `skill_view` and call `triple_plus_one(value=14)` (`43`), and verify both `skill_view` and `triple_plus_one` execute cleanly and return `43` in Chat.
- Checks:
  - `tests/unit/architecture/test_card691_autoreiv_agora_handsfree.py` (`pytest.mark.guard`)

## Plan and decisions
- **Decision D1 (Product & Architecture — Approved)**: Use `user:*` on `platform/agents/autoreiv.md` and bind `write_skill_file` / `skill_view` on `agent-authoring` so `AutoReiv` automatically discovers and mounts any user Agora skill folder on demand while preserving specialist boundaries (`Developer` for repo coding, `Tutor` for education).

## Findings
- **Fixed in-area (`src/application/skills/user_catalog.py`)**: `UserSkillCatalog._allowed_skill_ids_for_current_agent()` expanded `AUTO_SKILL_WILDCARD` (`*`) when authorizing `skill_view`, but had not yet expanded `AUTO_USER_SKILL_WILDCARD` (`user:*`). Fixed in `_allowed_skill_ids_for_current_agent()` and covered by both `test_card691_autoreiv_agora_handsfree.py` and `card-691-hands-free-agora-skill-authoring-and.mjs`.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-691-hands-free-agora-skill-authoring-and` | `desktop` | PASS | `AutoReiv` auto-discovered `handsfree-math/triple_plus_one` via `user:*` and executed `skill_view` -> `triple_plus_one(value=14)` -> `43` in Chat |
| `card-691-hands-free-agora-skill-authoring-and` | `phone` | PASS | `AutoReiv` auto-discovered `handsfree-math/triple_plus_one` via `user:*` and executed `skill_view` -> `triple_plus_one(value=14)` -> `43` in Chat |

Screenshots:
- `/tmp/autoreiv-qa/card-691/card-691-hands-free-agora-skill-authoring-and-desktop-02-in-chat-autoreiv-opens-handsfree-math-with-skill.png`
- `/tmp/autoreiv-qa/card-691/card-691-hands-free-agora-skill-authoring-and-phone-02-in-chat-autoreiv-opens-handsfree-math-with-skill.png`

## Release note
- `AutoReiv` now auto-discovers user Agora skill folders via `user:*` without manual ticking in Agent Studio and can author `SKILL.md`, `references/*.md`, and `tools/*.py` directly in Chat through `agent-authoring` [CARD-691].
