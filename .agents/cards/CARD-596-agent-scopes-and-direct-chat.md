---
id: CARD-596
title: "Agent scopes and direct chat: each agent keeps to its scope, the user picks who to talk to; only Architect/Toolsmith hand off to Developer"
status: Ready
created: 2026-10-01
branch: qa
related:
  - CARD-546
  - CARD-539
  - CARD-563
  - CARD-571
labels:
  - type:architecture
  - area:agents
  - area:chat
  - P1
needs_decision: none
milestone: M25
---

# [CARD-596] Agent scopes and direct chat: each agent keeps to its scope, the user picks who to talk to; only Architect/Toolsmith hand off to Developer

> **Status**: Ready (filed 2026-10-01)
> **Labels**: `type:architecture`, `area:agents`, `area:chat`, `P1`

## Why

Decided by Jacob (Oct 1, 2026): agents get deliberate scopes and the user picks who to talk to. Model-driven routing was unreliable on nemotron. In CARD-546, AutoReiv handed study requests to Tutor in only 2/10 runs.

Scopes:
- **AutoReiv**: general wiki work, templates and docs. No education skills.
- **Tutor**: only educational wiki resources (study, flashcards, quizzes, progress).

Hand-offs:
- The only hand-off kept is **Architect/Toolsmith → Developer** for coding.
- AutoReiv no longer hands off to Tutor. Asked a study question, it tells the user to open Tutor.

## Hand-offs that exist today (verified on qa `ad2e994f`)

1. **`handoff_to_agent` + `lookup_agents` are on every agent that has tools.**
   - They are in `REQUIRED_PLATFORM_TOOLS` (`src/application/agent_skills/schema.py`), so AutoReiv, Tutor, Developer and Toolsmith all get them.
   - Architect is excluded via `WITHHELD_PLATFORM_TOOLS` (`allowed_tools.py`, CARD-563). Direct has no tools.
2. **Skills that also list them:**
   - `coordination` (ticked on AutoReiv).
   - `agent-authoring` (AutoReiv). Its step 4 hands tool/MCP builds to `developer`, which contradicts Developer's prompt ("building AutoReiv tools is Toolsmith's job").
3. **Prompt wording that sends agents to `lookup_agents` + `handoff_to_agent`:**
   - the generated domain line (`allowed_tools.domain_line`, every non-Direct agent except Architect);
   - `good_agent_instructions.py:50` (the template for new agents);
   - `platform/agents/autoreiv.md` lines 26 and 45 (also "shell → developer");
   - `platform/agents/tutor.md` line 22 (also "destructive → developer");
   - `platform/skills/platform-health/SKILL.md` (shell → developer).
4. **`hand_off_card`: Architect → Developer** (skills `hand-off` and `review`). **Kept.**
5. **The UI "Ask Developer" buttons and tool-escalation cards open a Toolsmith chat** (CARD-571/520). The operator starts these; they are not model hand-offs. Kept.
6. **Toolsmith → Developer:** no explicit path. Only the generic `handoff_to_agent` it inherits from the required tools.

## Scope

1. **Remove `handoff_to_agent` and `lookup_agents` from `REQUIRED_PLATFORM_TOOLS`.**
   - Toolsmith gets `handoff_to_agent` through a skill, limited to target `developer`; the tool refuses any other target.
   - Architect keeps `hand_off_card` only.
   - No other agent can hand off.
2. **AutoReiv:**
   - untick `socratic-tutoring` and `coordination`;
   - tick `wiki-templates` (see CARD-598);
   - in `agent-authoring`, replace the hand-off to developer with "use the Ask Developer button (opens Toolsmith)";
   - drop the "shell → developer" lines (AutoReiv has no shell; it says so).
3. **Tutor:** scope is educational wiki resources only. Remove the `lookup_agents`/hand-off wording.
4. **Out-of-scope reply.** The generated domain line names the agent's scope and, for anything else, tells the user which agent to open. It is built from a short roster of the other agents (name: ticked skill names); no tool call.
   - Example: "That's a study request; open Tutor in Chat."
   - Keep the no-refusal tone and the Ask Developer line when no agent covers it.
5. **The user picks the agent in Chat** (the agent picker already exists). Optional, small: an "Open Tutor" chip on a reply that names another agent. Plain wording, no metaphors.
6. **ADR:** amend ADR-0061 (D6 routing) and ADR-0052 section 4 (dispatch to the covering agent): agents do not route; users pick.
7. **Tests and journeys:**
   - Update the CARD-539 out-of-domain journey: a study request to AutoReiv gets "open Tutor" and no hand-off.
   - Update the unit tests that expect hand-off tools on every agent.

## Out of scope

- A router or routing check (CARD-546 design, superseded).
- Conversation continuity across agents.
- Memory changes (CARD-597).

## Acceptance criteria

- `resolve_allowed_tools`:
  - AutoReiv, Tutor and Developer have neither `handoff_to_agent` nor `lookup_agents`;
  - Toolsmith has `handoff_to_agent`, which refuses targets other than `developer`;
  - Architect has `hand_off_card` only.
- AutoReiv's ticked skills include no education skill. Tutor's ticked skills are education-only.
- Live (nemotron, throwaway :8770), the CARD-546 study prompt ("Start my flashcard due review...") sent to AutoReiv, 5 runs:
  - each reply tells the user to open Tutor;
  - no hand-off, and no wiki search loop.
- The same prompt sent to Tutor runs the due review.
- Architect → Developer (`hand_off_card`) and Toolsmith → Developer still work (existing tests and journeys green).
- Fast preflight, full smoke and the routing journey are green on desktop and phone.
