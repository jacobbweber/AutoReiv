---
name: Agent Capability Intake
description: Use when the operator asks to teach an agent something, give it a new capability, or have it learn to do something new. Open with skill_view(skill_id="agent-authoring"). Inspect the agent, write Agora skill folders (SKILL.md, references/*.md, tools/*.py) with write_skill_file, or point to Ask Developer (opens Toolsmith), Capabilities Studio, or Agent Studio.
tools:
- inspect_agent
- list_available_skills_and_tools
- skill_view
- write_skill_file
- propose_skill
version: 3.1.0
tier: platform
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: The request ends in a written Agora skill folder (write_skill_file), Ask Developer (opens Toolsmith) with a brief, a skill proposal (propose_skill), or Agent Studio for a new agent.
---

# Agent Capability Intake

Use this when the operator wants an agent to be able to do something new: "teach AutoReiv to ...", "give the agent a new capability", "can it learn to ...".

## Protocol

1. **Find the agent and existing capabilities.** Use `inspect_agent` or `list_available_skills_and_tools` to read its current tools and skills. Do not duplicate something the agent already has.
2. **Clarify only if ambiguous.** If the operator already gave clear requirements (skill id, markdown instructions, or Python tool logic), act directly. Otherwise ask 1-2 focused questions first.
3. **Pick the route:**
   - **Agora skill folder (`write_skill_file`)**: Write `SKILL.md`, `references/<name>.md`, or `tools/<tool_name>.py` directly under `$DATA_DIR/skills/<skill_id>/`. When writing `tools/<tool_name>.py`, define a module-level `def run(...)` with type annotations and a docstring (plus optional `RISK = "read_only"`). `ToolCheckService` runs automatically on save: pure `read_only` tools with zero outside access auto-enable and mount immediately in this session; tools with outside access (`network`, `files`, `programs`) save disabled so the operator can inspect and enable them in **Capabilities** (`#view-capabilities`).
   - **Ask Developer (opens Toolsmith) or skill proposal (`propose_skill`)**: When the operator wants a parked proposal or a complex multi-host integration brief, use `propose_skill` or provide a brief for the Ask Developer button.
   - **A new agent**: Tell the operator to create it in Agent Studio (New Agent). There is no tool that creates agents.
4. **Report honestly.** State the exact `skills/<skill_id>/` files written, whether any `tools/<name>.py` was auto-enabled or saved disabled for review in **Capabilities**, and the next step.
