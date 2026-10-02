---
name: Agent Capability Intake
description: Use when the operator asks to teach an agent something, give it a new capability, or have it learn to do something new. Open with skill_view(skill_id="agent-authoring"). Inspect the agent, ask what is missing, then point a tool or MCP need to Ask Developer (opens Toolsmith), a skill to Skill Studio, and a new agent to Agent Studio.
tools:
- inspect_agent
- propose_skill
version: 3.0.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The request ends in exactly one route - Ask Developer (opens Toolsmith) with a brief, a skill proposal (Skill Studio or propose_skill), or Agent Studio for a new agent.
---

# Agent Capability Intake

Use this when the operator wants an agent to be able to do something new: "teach AutoReiv to ...", "give the agent a new capability", "can it learn to ...". Work out what is missing, then send it to the one place that builds it. You do not build tools here, and nothing is "trained".

## Protocol

1. **Find the agent.** Use `inspect_agent` to read its current tools and skills. Do not propose something the agent already has.
2. **Ask what is missing.** Before proposing, ask a few focused questions and wait for the answers: what the operator is trying to do, where it runs (this machine or a remote host), the exact commands, APIs or file formats, and what a good result looks like.
3. **Pick the route.**
   - **A new tool or MCP server** (a callable that does not exist yet): write a short brief (target agent, what the tool does, inputs and outputs, host, reference docs).
   - **A new skill** (a procedure that combines tools the agent already has): draft it for `propose_skill`, or tell the operator to open Skill Studio to write and save it.
   - **A new agent**: tell the operator to create it in Agent Studio (New Agent) and tick the skills it needs. There is no tool that creates agents.
4. **Show the brief and get a yes.** Show the brief or proposal and wait for the operator's yes before acting.
5. **Act on the yes.**
   - Tool or MCP: tell the operator to use the Ask Developer button (opens Toolsmith) with the brief. Toolsmith writes, checks and registers the tool.
   - Skill: call `propose_skill` with the draft, or point to Skill Studio.
6. **Report honestly.** Tell the operator clearly what was proposed and what the next step is.

## Done-when

- The agent's current tools and skills were checked with `inspect_agent`.
- The operator answered the questions and said yes to the brief.
- The request went to exactly one route: Ask Developer (opens Toolsmith) with a brief, a skill proposal, or Agent Studio for a new agent.
- The operator was told where to follow it up (Ask Developer button, Skill Studio or Agent Studio).
