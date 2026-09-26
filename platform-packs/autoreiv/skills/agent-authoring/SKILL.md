---
name: Agent Capability Intake
description: "Use when the operator asks to teach an agent something, give it a new capability, or have it learn to do something new. Open with skill_view('agent-authoring'). Inspect the agent, ask what is missing, then hand a tool or MCP need to the Developer, a skill to Skill Studio, and a new agent to build-agent-pack."
version: 2.1.0
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

Use this when the operator wants an agent to be able to do something new: "teach AutoReiv to ...", "give the agent a new capability", "can it learn to ...". Work out what is missing, then send it to the one place that builds it. You do not build tools here, and nothing is "trained".

## Protocol

1. **Find the agent.** Use `lookup_agents` to confirm the agent id, then `inspect_agent_pack` to read its current tools and skills. Do not propose something the agent already has.
2. **Ask what is missing.** Before any handoff, ask a few focused questions and wait for the answers: what the operator is trying to do, where it runs (this machine or a remote host), the exact commands, APIs or file formats, and what a good result looks like.
3. **Pick the route.**
   - **A new tool or MCP server** (a callable that does not exist yet): write a short brief (target agent, what the tool does, inputs and outputs, host, reference docs).
   - **A new skill** (a procedure that combines tools the agent already has): draft it for `propose_skill`, or tell the operator to open Skill Studio to write and save it.
   - **A new agent**: follow the `build-agent-pack` runbook.
4. **Show the brief and get a yes.** Show the brief or proposal and wait for the operator's yes before acting.
5. **Act on the yes.**
   - Tool or MCP: call `handoff_to_agent(target_agent_id="developer", task_directive=<brief>)`. Use exactly these argument names. The Developer builds, checks and registers the tool, and its result comes back in this chat.
   - Skill: call `propose_skill` with the draft, or point to Skill Studio.
6. **Report honestly.** If a tool call fails, tell the operator what failed and what you will do next. Never replace a failed handoff with general advice.

## Done-when

- The agent's current tools and skills were checked with `inspect_agent_pack`.
- The operator answered the questions and said yes to the brief.
- The request went to exactly one route: a Developer handoff with a brief, a skill proposal, or build-agent-pack.
- The operator was told where to follow it up (this chat for the Developer result, Skill Studio or Agent Studio).
