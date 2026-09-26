---
name: Agent Capability Intake
description: "Capability intake: inspect the agent, then route a tool or MCP need to Developer, a skill to Skill Studio, and a new agent to build-agent-pack."
version: 2.0.0
tier: platform
requires_tools:
  - inspect_agent_pack
  - lookup_agents
  - handoff_to_agent
  - propose_skill
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The request ends in exactly one route - a Developer handoff with a brief, a skill proposal (Skill Studio or propose_skill), or the build-agent-pack runbook.
---

# Agent Capability Intake

Use this when the operator wants an agent to be able to do something new. Work out what is missing, then send it to the one place that builds it. You do not build tools here, and nothing is "trained".

## Protocol

1. **Find the agent.** Use `lookup_agents` to confirm the agent id, then `inspect_agent_pack` to read its current tools and skills. Do not propose something the agent already has.
2. **Ask what is missing.** A few focused questions: what the operator is trying to do, where it runs (this machine or a remote host), the exact commands, APIs or file formats, and what a good result looks like.
3. **Pick the route.**
   - **A new tool or MCP server** (a callable that does not exist yet): write a short brief (target agent, what the tool does, inputs and outputs, host, reference docs) and call `handoff_to_agent` to the `developer` agent with that brief. The Developer builds, checks and registers it.
   - **A new skill** (a procedure that combines tools the agent already has): call `propose_skill` with the draft, or tell the operator to open Skill Studio to write and save it.
   - **A new agent**: follow the `build-agent-pack` runbook.
4. **Confirm before acting.** Show the brief or proposal and get the operator's yes before the handoff or proposal.

## Done-when

- The agent's current tools and skills were checked with `inspect_agent_pack`.
- The request went to exactly one route: a Developer handoff with a brief, a skill proposal, or build-agent-pack.
- The operator was told where to follow it up (the Developer chat, Skill Studio or Agent Studio).
