---
id: CARD-537
title: "AutoReiv refuses the weather question even after the Developer granted it get_weather (\"outside my authorized domain\")"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-520
  - CARD-532
labels:
  - type:product
  - area:agents
  - P2
---

# [CARD-537] A newly granted tool is not used: AutoReiv stays in its narrow domain

> **Status**: Ready (found by the CARD-532 live QA runner, 2026-09-26 ~6:56 PM ET). D1 decided by Jacob on 2026-09-26: a granted tool widens the agent's domain. Not built yet.
> **Related**: CARD-520 (the Teach -> Needs a tool -> Ask Developer loop), CARD-532 (journey `card-520-teach-needs-tool`)
> **Labels**: `type:product`, `area:agents`, `P2`

## Evidence

- Journey `card-520-teach-needs-tool`, desktop and phone, fresh throwaway env, real vLLM: the Developer registers `get_weather` and it appears in `allowed_tool_names` for autoreiv (step 4 passes). Asking AutoReiv "What is the weather in Boston right now?" again, in the same chat and in a brand-new chat, gives no tool call. The reply: "I'm unable to provide weather information. My domain is limited to platform SRE health, daily task coordination, wiki vault curation, and host diagnostics."
- Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-532\rerun-520\card-520-teach-needs-tool-desktop-06-a-new-autoreiv-chat-answers-the-weather-question.png`.
- Not yet diagnosed: whether the tool reaches the model's tool list for that turn (capability subset / catalog match) or the system prompt's domain wording wins.

## Acceptance criteria (EARS)

- **REQ-537-001 (a granted tool is in scope):** THE SYSTEM SHALL treat every tool ticked for an agent (for example `get_weather` granted to autoreiv by the Developer) as part of that agent's domain, in addition to the domain stated in its system prompt.
- **REQ-537-002 (no refusal when a ticked tool can answer):** WHEN a question can be answered by a tool ticked for the agent, THE agent SHALL call that tool and SHALL NOT refuse the question as outside its domain.
- **REQ-537-003 (next turn sees the grant):** WHEN a tool is newly granted to an agent, THE SYSTEM SHALL include it in that agent's tool list from the next turn, in an existing chat and in a new chat.

## Decisions

- **D1 (product) - decided by Jacob on 2026-09-26:** When an operator has AutoReiv's Developer build and grant a tool, AutoReiv uses it even outside its stated domain. **Answer: yes (the recommended option). A tool granted to AutoReiv widens its domain, so it should use it.** Captured in REQ-537-001 and REQ-537-002.
- **D2 (technical, after D1):** make sure a newly granted tool is in the next turn's tool list (catalog match / capability subset), with a unit test and the CARD-532 journey step 5/6 turning from WARN to PASS.

## Done when

The CARD-520 journey passes all six steps on desktop and phone: AutoReiv calls the granted tool for the question, in the same chat and in a new chat.
