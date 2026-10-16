---
id: CARD-688
title: "Auto-scoped agents and session-mounted skill tools on demand"
type: feature
status: In Review
priority: P1
milestone: M26
needs_decision: none
proof:
  journeys: [card-687-agora-skill-folder-loader, card-688-auto-scoped-session-skills]
  checks:
    - tests/unit/architecture/test_card688_auto_scoped_session_skills.py
    - tests/integration/test_card688_auto_scoped_session_contract.py
branch: feat/card-687-agora-skill-folder-loader
log: {minutes: 45, qa_runs: 2, findings: 0}
created: 2026-10-15
---

# CARD-688 Auto-scoped agents and session-mounted skill tools on demand

## Intent
Jacob wants to eliminate the hands-on human tax of manually scoping and ticking every skill on an agent in Agent Studio while keeping per-turn context lean. When an agent is configured with `skills: ["*"]` ("Auto-discover all skills"), it should automatically discover any enabled skill folder on disk via the lightweight progressive skill index and dynamically mount that skill's tools into the active session only when the agent opens the skill with `skill_view(skill_id)`.

## Goal
1. An agent with `"*"` in `allowed_skill` (or `skills:` in `agents/<id>.md`) automatically discovers all non-hidden skills (`ticked_skills(agent)` expands `"*"`), including newly created Agora skill folders without touching Agent Studio.
2. On a fresh turn for an `"*"` auto-scoped agent, `AgentKernel._resolve_active_tools` sends only `REQUIRED_PLATFORM_TOOLS`, `skill_view`, `list_user_skills`, and tools of any explicitly pinned skills listed alongside `"*"` (`pinned_skills(agent)`), avoiding the token cost of every skill's tool schemas upfront.
3. Calling `skill_view(skill_id)` during a session activates `skill_id` for that session (persisted in session transcript history and in-memory session state), refreshes `active_tools` on the next ReAct step, and mounts the skill's enabled tools so the agent can call them immediately.
4. Agent Studio (`forge.js` / `runbook.js`) provides an `Auto-discover all skills (*)` switch (`data-skill-id="*"`) so the operator can toggle hands-free skill discovery on any agent.

## Change
- `src/application/agent_skills/allowed_tools.py`:
  - Add `AUTO_SKILL_WILDCARD = "*"`, `has_auto_skill_wildcard(agent)`, and `pinned_skills(agent)`.
  - Expand `"*"` in `ticked_skills(agent)` to all non-hidden skill IDs in `ContentStore().skills.list()`.
- `src/application/skills/session_skills.py` (new module, extracted to keep `user_catalog.py` and `agent_kernel.py` under size limits):
  - `record_session_skill_activation(session_id, skill_id)`, `get_session_activated_skills(session_id, history)`, `clear_session_skill_activations()`.
  - `resolve_turn_active_tools(...)`: implements `AgentKernel._resolve_active_tools`, narrowing `"*"` auto-scoped agents to `REQUIRED_PLATFORM_TOOLS` + `skill_view` + `list_user_skills` + `pinned_skills(agent)` + session-activated skills while preserving all-at-once loading for fixed-list agents (`CARD-578`).
- `src/application/skills/user_catalog.py`:
  - Expand `"*"` in `render_skill_index` and `_allowed_skill_ids_for_current_agent`.
  - In `skill_view`, record session skill activation for the active `session_id`, ensure any enabled colocated tools for that skill are mounted in `self.tool_registry`, and return `activated_tools` in the `skill_view` response when tools are mounted.
- `src/application/kernel/agent_kernel.py`:
  - Delegate `_resolve_active_tools` to `resolve_turn_active_tools` (passing `session_id` and `history`).
  - Refresh `active_tools, offered_names, system_msg` after tool execution inside `run_turn` and `stream_turn` so calling `skill_view(skill_id)` in step $N$ mounts that skill's tools in step $N+1$ of the same turn.
- `src/web/static/modules/studios/forge/runbook.js`:
  - Render the `Auto-discover all skills (*)` switch (`#forgeAutoDiscoverSkills`, `data-skill-id="*"`) above `#forgeSkillsGrid` in Agent Studio.
- `docs/adr/0065-agora-skill-folders-and-unified-capabilities.md`:
  - Link `CARD-688` and its guard test.

## What dies
nothing

## Proof
- Journey `card-688-auto-scoped-session-skills`:
  1. Opens Agent Studio (`#forge`), switches `AutoReiv` to `Auto-discover all skills (*)` via the `#forgeAutoDiscoverSkills` toggle, and saves.
  2. Creates a brand-new Agora skill folder `skills/agora-dice-roller/` with `SKILL.md` and `tools/roll_weighted_dice.py` AFTER saving and enables the tool via `/api/capabilities/skills/agora-dice-roller/tools/roll_weighted_dice/toggle`.
  3. Verifies via `/api/agents/autoreiv` that `allowed_skill` contains `"*"` and `agora-dice-roller` was never manually ticked, yet `roll_weighted_dice` is authorized.
  4. Runs a chat turn in Chat with `AutoReiv` asking it to open `agora-dice-roller` with `skill_view` and call `roll_weighted_dice(sides=12, bonus=5)`, proving the agent discovers the unticked skill, activates it via `skill_view`, and executes `roll_weighted_dice` in the next step of the same turn (`roll_total = 17`).
- Checks:
  - `tests/unit/architecture/test_card688_auto_scoped_session_skills.py` (`pytest.mark.guard`)
  - `tests/integration/test_card688_auto_scoped_session_contract.py`

## Plan and decisions
- Approved by Jacob (`Option 1`, `Option A`, `build`, and *"Let's batch slice 2 into this as well"* under `ADR-0065`).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-687-agora-skill-folder-loader` | desktop | PASS | Tree verified for `agora-checksum` (`SKILL.md`, `references/guide.md`, `tools/calc_checksum.py`); `Architect` granted colocated tool `calc_checksum` |
| `card-687-agora-skill-folder-loader` | phone | PASS | Tree verified for `agora-checksum` (`SKILL.md`, `references/guide.md`, `tools/calc_checksum.py`); `Architect` granted colocated tool `calc_checksum` |
| `card-688-auto-scoped-session-skills` | desktop | PASS | `AutoReiv` saved with `Auto-discover all skills (*)`; unticked `agora-dice-roller` auto-granted `roll_weighted_dice` via `*`; session executed `skill_view -> roll_weighted_dice` (`roll_total = 17`) |
| `card-688-auto-scoped-session-skills` | phone | PASS | `AutoReiv` saved with `Auto-discover all skills (*)`; unticked `agora-dice-roller` auto-granted `roll_weighted_dice` via `*`; session executed `skill_view -> roll_weighted_dice` (`roll_total = 17`) |

Screenshots:
- `/tmp/autoreiv-qa/card-688/card-688-auto-scoped-session-skills-desktop-01-toggle-auto-discover-all-skills-on-autoreiv-in-a.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-688\card-688-auto-scoped-session-skills-desktop-01-toggle-auto-discover-all-skills-on-autoreiv-in-a.png`)
- `/tmp/autoreiv-qa/card-688/card-688-auto-scoped-session-skills-desktop-03-open-chat-and-verify-autoreiv-activates-agora-di.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-688\card-688-auto-scoped-session-skills-desktop-03-open-chat-and-verify-autoreiv-activates-agora-di.png`)
- `/tmp/autoreiv-qa/card-688/card-688-auto-scoped-session-skills-phone-01-toggle-auto-discover-all-skills-on-autoreiv-in-a.png` (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-688\card-688-auto-scoped-session-skills-phone-01-toggle-auto-discover-all-skills-on-autoreiv-in-a.png`)

## Release note
Added `skills: ["*"]` auto-scoped skill discovery and on-demand session tool mounting when an agent opens a skill with `skill_view` (CARD-688, ADR-0065).
