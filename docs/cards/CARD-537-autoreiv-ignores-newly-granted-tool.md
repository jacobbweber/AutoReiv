---
id: CARD-537
title: "AutoReiv refuses the weather question after the Developer built get_weather: use an accepted skill tool, route instead of refusing"
status: Ready
created: 2026-09-26
branch: qa
depends_on:
  - CARD-539
related:
  - CARD-539
  - CARD-520
  - CARD-532
labels:
  - type:product
  - area:agents
  - P2
---

# [CARD-537] An accepted skill tool is used; out-of-domain requests are routed, not refused

> **Status**: Ready, **blocked by [CARD-539](CARD-539-capability-scoping-one-allowed-tools-function.md)** (found by the CARD-532 live QA runner, 2026-09-26 ~6:56 PM ET). D1 decided by Jacob on 2026-09-26 (reworded under [ADR-0061](../adr/0061-capability-scoping-skills-only-permission-one-enforcement-point.md)).  
> **Related**: CARD-520 (Teach -> Needs a tool -> Ask Developer), CARD-532 (journey `card-520-teach-needs-tool`)  
> **Labels**: `type:product`, `area:agents`, `P2`

## Evidence

- Journey `card-520-teach-needs-tool`, desktop and phone, fresh throwaway env, real vLLM: the Developer registers `get_weather` and `NativeToolService._grant` appends it to AutoReiv's `allowed_tool_names` (step 4 passes). Asked "What is the weather in Boston right now?" again, in the same chat and a new chat, AutoReiv makes no tool call and replies: "I'm unable to provide weather information. My domain is limited to platform SRE health, daily task coordination, wiki vault curation, and host diagnostics."
- Screenshot: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-532\rerun-520\card-520-teach-needs-tool-desktop-06-a-new-autoreiv-chat-answers-the-weather-question.png`.
- Diagnosed (2026-09-26): `ScopedToolRegistry.get_tools_for_agent` ignores `allowed_tool_names` for `autoreiv`, so the tool is callable at `_execute_inner` but never in the model's tool list; the pack prompt's `[DOMAIN BOUNDARIES & REFUSALS]` text then makes it refuse. The grant is also invisible in Agent Studio and dropped by the next Save. CARD-539 removes all three causes.

## Acceptance criteria (EARS)

- **REQ-537-001 (an accepted skill tool is in scope):** WHEN Jacob accepts a proposal that ticks or extends a skill for an agent, THE SYSTEM SHALL treat that skill's tools as part of the agent's domain, and the generated domain line SHALL include it.
- **REQ-537-002 (use, route, never refuse):** WHEN a question can be answered by a tool of the agent's ticked skills, THE agent SHALL call it. WHEN it cannot but another agent's skills can, THE agent SHALL hand off. WHEN no agent can, THE agent SHALL say so and offer Ask Developer. THE agent SHALL NOT answer with refusal wording.
- **REQ-537-003 (next turn sees the acceptance):** WHEN a proposal is accepted, THE SYSTEM SHALL include the skill's tools in that agent's allowed set from the next turn, in an existing chat and a new chat.

## Decisions

- **D1 (product), decided by Jacob on 2026-09-26:** An accepted skill tool widens the agent's domain. (Originally recorded as "a granted tool widens the domain"; reworded after ADR-0061 removed direct tool grants. Only a tool Jacob accepted into a ticked skill counts, so no control is bypassed.)
- **D2 (technical):** The refusal fix is route-not-refuse (ADR-0061 rule 6), delivered by CARD-539's prompt and router changes; this card verifies it end to end.

## Done when

After CARD-539: the updated CARD-520 journey passes on desktop and phone (proposal to attach `get_weather` to a skill of AutoReiv, accepted, the skill shows ticked in Agent Studio, AutoReiv answers the weather question in the same chat and a new chat), and the routing journey shows a handoff instead of a refusal.
