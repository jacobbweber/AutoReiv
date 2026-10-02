---
id: CARD-596
title: "Agent scopes and direct chat: each agent keeps to its scope, the user picks who to talk to; only Architect/Toolsmith hand off to Developer"
status: Done
completed: 2026-10-01
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
proof:
  journeys:
    - card-596-agent-scopes-and-direct-chat
    - card-539-out-of-domain-routing
  checks:
    - preflight-fast
log: {minutes: 55, qa_runs: 4, findings: 0}
---

# [CARD-596] Agent scopes and direct chat: each agent keeps to its scope, the user picks who to talk to; only Architect/Toolsmith hand off to Developer

> **Status**: Done
> **Labels**: `type:architecture`, `area:agents`, `area:chat`, `P1`

## Problem

Model-driven routing across general chat agents was unreliable on local models (e.g. nemotron / qwen3.8). In CARD-546, AutoReiv handed study requests to Tutor in only 2/10 runs, frequently getting trapped in wiki search loops or refusing requests. Furthermore, `handoff_to_agent` and `lookup_agents` were present in `REQUIRED_PLATFORM_TOOLS` on every agent, blurring boundaries and enabling invalid delegations.

## Cause

1. `handoff_to_agent` and `lookup_agents` were globally declared in `REQUIRED_PLATFORM_TOOLS`.
2. AutoReiv had educational skills (`socratic-tutoring`) and `coordination` ticked.
3. System prompts and `domain_line()` instructed agents to execute model routing tool calls rather than directing the user to chat with the covering specialist directly.

## Change

1. Removed `handoff_to_agent` and `lookup_agents` from `REQUIRED_PLATFORM_TOOLS` (`src/application/agent_skills/schema.py`).
2. Granted `handoff_to_agent` strictly to Toolsmith via `platform/skills/native-tool-engineering/SKILL.md`.
3. Enforced fail-closed target verification in `handoff_to_agent` (`src/application/skills/orchestration_tools.py`) refusing any target other than `developer`. Architect retains `hand_off_card`.
4. Scoped AutoReiv (`platform/agents/autoreiv.md`): unticked `socratic-tutoring` and `coordination`, scrubbed hand-off tool instructions and shell delegation text.
5. Scoped Tutor (`platform/agents/tutor.md`): limited strictly to educational wiki resources, scrubbed hand-off and shell delegation text.
6. Updated `domain_line()` (`src/application/agent_skills/allowed_tools.py`) and `good_agent_instructions.py`: builds a concise roster of covering agents and directs the user to open the appropriate agent in Chat, ending with "You can use Ask Developer to add this." when unhandled.
7. Updated `platform/skills/agent-authoring/SKILL.md` and `platform/skills/platform-health/SKILL.md`: removed `lookup_agents`/`handoff_to_agent`, directing tool requests to Ask Developer (Toolsmith).
8. Amended ADR-0061 (Rule 6) and ADR-0052 (Section 4).

## What dies

- `handoff_to_agent` and `lookup_agents` as default platform tools.
- AutoReiv model routing to Tutor.
- Shell-to-developer delegation prompt instructions on AutoReiv and Tutor.

## Findings

None (all in-area assertions passed).

## Results

### Live QA

| Journey | Viewport | Outcome | Note |
|---|---|---|---|
| `card-596-agent-scopes-and-direct-chat` | desktop | PASS | AutoReiv directs to Tutor/Developer; Tutor runs study; Ask Developer button shown |
| `card-596-agent-scopes-and-direct-chat` | phone | PASS | Full journey green on mobile viewport |
| `card-539-out-of-domain-routing` | desktop | PASS | Regression run green |
| `card-539-out-of-domain-routing` | phone | PASS | Mobile regression run green |

### Screenshots

- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-596\card-596-agent-scopes-and-direct-chat-desktop-01-study-request-to-autoreiv-directs-to-tutor-in-ch.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-596\card-596-agent-scopes-and-direct-chat-desktop-02-study-request-to-tutor-tutor-executes-study-turn.png`
- `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\card-596\card-596-agent-scopes-and-direct-chat-desktop-04-request-nobody-covers-says-so-and-offers-ask-dev.png`

## Release note

Scoped agents to their designated domains and shifted routing to direct chat selection by the operator. Removed `handoff_to_agent` and `lookup_agents` from default platform tools, restricting `handoff_to_agent` exclusively to Toolsmith targeting Developer for coding tasks. Out-of-scope requests now clearly guide the user to the covering agent in Chat or offer the Ask Developer button.
