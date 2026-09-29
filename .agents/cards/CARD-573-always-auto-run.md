---
id: CARD-573
title: "Agent Studio: Always auto-run preference per agent"
type: feature
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof: "Journey card-573-always-auto-run: tick Always auto-run in Agent Studio > Agent Preferences for an agent and save; a new chat with that agent opens with the Chat Auto-run box checked; unticking it sends approval_mode ask and sticks for that chat only (another new chat with the agent starts checked again); a new routine for that agent opens with its Auto-run box checked, while existing routines keep their saved value. Checks: test_card573_always_auto_run.py, vitest card_573_always_auto_run.test.js."
branch: feat/card-573-always-auto-run (stacked on feat/card-572-explicit-job: both change the Chat composer toggles in runtime_toggles.js / chat.js on 572; 573 hooks the per-chat apply into chat/session_select.js)
created: 2026-09-29
related: [CARD-572, CARD-470, CARD-299]
---

# CARD-573 Agent Studio: Always auto-run preference per agent

> **Status**: Ready

## Why
Jacob trusts some agents to run write, shell and code tools without asking. Today the Chat Auto-run box is one
remembered choice for every agent (CARD-470), so he either flips it on every time he switches agents or leaves it on
for agents he does not trust.

## Decisions
- D1 (Jacob): an **Always auto-run** preference per agent in Agent Studio (Agent Preferences, same pattern as Max turns /
  Session cleanup: a field on the agent file, `always_auto_run`, default off; also settable through the agent
  customization override). When on, the Chat Auto-run box starts checked for every chat/session with that agent.
  Jacob can still untick it per chat; that choice sticks for that chat only.
- D2 (proposed by the parent agent, Jacob can revise): **Routines** keep their own Auto-run box and its saved value
  always wins. A **new** routine created for an agent with Always auto-run on starts with its box checked (form and
  API when `approval_mode` is not sent). Existing routines are unchanged.
- Agents without the preference keep today's behaviour (CARD-470: the last Auto-run choice is remembered).

## Scope
1. `AgentProfile.always_auto_run` (default false), saved in the agent file (only when on), in the Agent Studio payload,
   the public agent JSON and `AgentCustomization`.
2. Agent Studio: checkbox in Agent Preferences.
3. Chat: when the selected session's agent has it on, the Auto-run box is checked unless Jacob unticked it in that chat
   (per-chat choice kept in browser storage); re-applied on session switch and when the roster reloads.
4. Routines: the form pre-checks Auto-run for a new routine of such an agent (also when the agent is changed in the new
   form); the API uses the agent preference only when `approval_mode` is omitted on create; an update that omits it keeps
   the saved value.

## Done when
- Setting the preference, opening a new chat -> box checked; untick -> that chat sends ask, a new chat starts checked.
- New routine for the agent -> box pre-checked; existing routines unchanged.
- Agents without it behave as before. Fast preflight GREEN; journey card-573-always-auto-run PASS.

## Log
- 2026-09-29: Jacob asked for this (D1); routine behaviour D2 proposed by the parent agent. Ready; building stacked on CARD-572.
