---
id: CARD-537
title: "AutoReiv refuses the weather question after the Developer built get_weather: use an accepted skill tool, route instead of refusing"
status: Done
created: 2026-09-26
branch: feat/card-537-accepted-skill-widens-domain
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

> **Status**: Done (merged to qa on 2026-09-27 after Jacob's "merge to qa" at 12:07 PM ET). It was In Review (2026-09-27 ~4:05 AM ET) on `feat/card-537-accepted-skill-widens-domain`, not merged or pushed. CARD-539 (merged) delivered the behavior; this card verifies it end to end and fixes Tutor's prompt. D1 was decided by Jacob on 2026-09-26 (reworded under [ADR-0061](../adr/0061-capability-scoping-skills-only-permission-one-enforcement-point.md)).  
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

## Implementation (2026-09-27)

No open decisions: D1 (Jacob) and D2 (ADR-0061 rule 6) cover it.

| Commit | What |
|---|---|
| `23fc6c59` | Tests: `test_card537_accepted_skill_widens_domain.py`, end to end through `NativeCustomToolService.register` -> pending proposal -> `apply_tool_attachment` -> a fresh read -> `resolve_allowed_tools`, `domain_line` and the kernel's per-turn list. New journey `card-537-accepted-skill-widens-domain`. These tests passed on the first run because CARD-539 already delivered the behavior. |
| `1a22597f` | Scavenger Pass fix (test first, confirmed failing): Tutor's pack prompt had a fixed "Focus strictly on tutoring ..." boundary that would contradict an accepted skill tool. It now points at the generated "Your domain" line and routes, and a parametrized test covers every platform pack. |

## Evidence

**Tests vs baseline** (full suite on `1a22597f`, smoke run on its own):

| Suite | Result | Baseline |
|---|---|---|
| Unit | 2072 passed, 11 skipped, 1 failed (CARD-454 linter) | same failure |
| Integration | 103 passed | 103 |
| Vitest | 949 passed, 3 failed (CARD-456) | same 3 |
| ESLint (`src/web/static`) | 4 errors, 5 warnings | 4 + 5 |
| Ruff | 7 | 7 |
| Smoke | 73 passed | 73 |

**Live QA** (real vLLM, throwaway env on :8770):

| Journey | Desktop | Phone |
|---|---|---|
| card-537-accepted-skill-widens-domain | PASS, 5/5 (14:05 in the same chat and a new chat) | Run 1 FAIL at step 4: the tool was called twice with the right result, then the cycle guard ended the turn (CARD-551). Rerun PASS, 5/5. |
| card-520-teach-needs-tool (regression) | PASS, 7/7 | PASS, 7/7 (weather tool is a stub, CARD-543) |
| card-539-out-of-domain-routing (Tutor prompt changed) | WARN: code to Developer pass, Tutor probe soft warn (CARD-546 / CARD-551), nobody-covers pass | WARN, the same |

Screenshots:
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-537\card-537-accepted-skill-widens-domain-desktop-04-same-chat-autoreiv-answers-with-the-accepted-too.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-537\card-537-accepted-skill-widens-domain-desktop-03-accept-the-proposal-in-agent-studio-the-skill-sh.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-537-phone2\card-537-accepted-skill-widens-domain-phone-05-new-chat-autoreiv-answers-with-the-accepted-tool.png`

**Follow-ups**: CARD-550 (no agent ticks the checkout tools; needs a decision) and CARD-551 (the cycle guard drops a good tool result).
