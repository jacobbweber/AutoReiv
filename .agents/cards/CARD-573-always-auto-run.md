---
id: CARD-573
title: "Agent Studio: Always auto-run preference per agent"
type: feature
status: In Review
priority: P2
milestone: M24
needs_decision: none
proof: "Journey card-573-always-auto-run: tick Always auto-run in Agent Studio > Agent Preferences for an agent and save; a new chat with that agent opens with the Chat Auto-run box checked; unticking it sends approval_mode ask and sticks for that chat only (another new chat with the agent starts checked again); a new routine for that agent opens with its Auto-run box checked, while existing routines keep their saved value. Checks: test_card573_always_auto_run.py, vitest card_573_always_auto_run.test.js."
branch: feat/card-573-always-auto-run (stacked on feat/card-572-explicit-job: both change the Chat composer toggles in runtime_toggles.js / chat.js on 572; 573 hooks the per-chat apply into chat/session_select.js)
created: 2026-09-29
related: [CARD-572, CARD-470, CARD-299]
---

# CARD-573 Agent Studio: Always auto-run preference per agent

> **Status**: In Review

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

## Results (2026-09-29, In Review)
- Agent: `AgentProfile.always_auto_run` (default off) in the agent file (written only when on), the Agent Studio payload
  (omitted = keep the saved value), public agent JSON and `AgentCustomization`.
- Agent Studio: **Always auto-run** checkbox in Agent Preferences (under Max turns / Session cleanup).
- Chat: `applySessionAutoRun` (runtime_toggles.js) runs on every chat select (chat/session_select.js) and when the roster
  reloads. Agent with the preference: box checked unless unticked in that chat (per-chat choice in browser storage
  `autoreiv_autorun_chat_choices_573`); other agents: CARD-470 remembered choice, unchanged. chat.js untouched (CARD-397 line cap).
- Routines: the form pre-checks Auto-run for a new routine of such an agent (also on agent change in the new form); the
  create API uses the agent preference only when `approval_mode` is omitted; an update that omits it keeps the saved value.
- Tests: `tests/unit/web/test_card573_always_auto_run.py` (3), vitest `card_573_always_auto_run.test.js`; full not-slow
  suite 2038 passed, 13 skipped; vitest 947; fast preflight --base qa GREEN.

| Journey | Viewport | Result | Notes |
|---|---|---|---|
| card-573-always-auto-run | desktop | PASS | Agent Studio tutor: ticked and saved (PUT sent always_auto_run true; autoreiv stays false). Tutor chat A opened with Auto-run checked (badge shown), Run as a job off beside it. Unticked in A: send carried approval_mode ask; tutor chat B still opened checked; A stayed unticked on return; an autoreiv chat opened unchecked. New tutor routine: box pre-checked, saved run; a saved ask routine kept ask; API create without approval_mode got run. |
- Follow-up (load timing): Agent Studio overwrote an edit made before the agent finished loading (a tick on the still-empty
  form was replaced when the load filled it in). Fix: the four agent sections start `inert` in index.html and stay inert
  while an agent is filled in; a newer render makes older ones stop after their awaits; a late load keeps the form the user
  picked; Save waits while busy. vitest `card_573_forge_load_timing.test.js`; the journey now ticks right after picking
  the agent (failed before the fix: "the tick was overwritten by the agent load"; PASS after).
- QA default model: `qwen3.8:latest` on Nimo Ollama (`scripts/live_qa.py`, live-qa skill); Developer journeys default to
  `qwen3.6:35b-a3b`. `qwen3.6:35b-a3b-65k` is gone from Nimo; `qwen3-coder:latest` is installed but its runner is killed
  on load while qwen3.8 and qwen3.6 are pinned in memory.

## Log
- 2026-09-29: Jacob asked for this (D1); routine behaviour D2 proposed by the parent agent. Ready; building stacked on CARD-572.
- 2026-09-29: Built; checks green; journey PASS; In Review. Not merged or pushed.
- 2026-09-29: Follow-ups: Agent Studio load-timing fix; QA default model qwen3.8:latest on Nimo. Journey PASS.
