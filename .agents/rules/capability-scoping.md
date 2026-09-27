---
trigger: always_on
description: Capability scoping (ADR-0061) - tools reach agents only through ticked skills; one function decides allowed tools.
---

# Rule: Capability scoping

Source: [ADR-0061](../../docs/adr/0061-capability-scoping-skills-only-permission-one-enforcement-point.md).

1. **One decider.** `resolve_allowed_tools(agent)` in `src/application/agent_packs/allowed_tools.py` (built by CARD-539) is the only place that decides which tools an agent may use: `REQUIRED_PLATFORM_TOOLS` plus tools bound to its ticked skills. The model's tool list, `_execute_inner` and `ToolPolicyGate` call it. Until CARD-539 lands, do not add logic to the old paths it replaces.
2. **No new side paths.** Never add another way for a tool to reach an agent: no per-agent tool lists or grants, no profile flags that add tools, no `agent.id == "autoreiv"` (or any id) special case, no mounting of unticked skills.
3. **Selection only narrows.** Intent matching, `activate_skill`, catalog matching and the per-turn clamp pick from the allowed set; an empty result never falls back to the full list.
4. **Every tool has a runbook.** A new tool ships bound to a skill with a `SKILL.md`.
5. **Growth is a proposal.** Code that builds or attaches tools creates a pending approval; only Jacob's acceptance changes permission, and it shows as a tick in Agent Studio.
6. **Route, do not refuse.** Prompts and templates never tell an agent to refuse out-of-domain work; they hand off, or offer Ask Developer when no agent covers it.
