---
name: Build Agent Pack
description: Write, import, and export one specialist Agent Pack matching the platform schema with Socratic discovery.
---

# Build Agent Pack

Use this runbook when the human wants a specialist packaged, imported, or exported. An Agent Pack is packaging, not a fourth primitive. Primitives stay agent, skill (one SKILL.md), and tool (one callable).

An agent has many skills. Each skill has tools. Skills belong to one agent. Ask for that shape, then write the nested pack.

## Tools

- `scaffold_agent_pack` - write a pack from a structured spec and import it
- `export_agent_pack` - export an existing agent id to a folder + zip under the data dir
- `import_agent_pack` - import a folder or zip path into user data

## Socratic Discovery Protocol

When the human proposes creating a new specialist agent (e.g., "I want an Ansible agent", "Create a database admin", or "I am ready to create a new agent"), do NOT immediately scaffold a naive 2-sentence prompt. Instead, conduct a concise Socratic Discovery interview by asking 3–4 high-leverage clarifying questions:

1. **Core Specialization**: What exact workflows, domains, or tasks should this agent master?
2. **Environment & Execution**: Where does it operate (local machine, remote SSH hosts from Credential Vault, containerized sandbox)?
3. **Safety & Guardrails**: What mutating operations require explicit human confirmation or mandatory dry-run `--check` modes?
4. **Initial Tool Needs**: Does it rely on existing catalog tools (`cli_exec`, `remote_tools`), or does it need dedicated tools trained in the Factory?

## Gold-Standard Prompt Blueprint

When synthesizing the agent's `system_prompt`, structure it with standard explicit sections:
- `[IDENTITY & ROLE]`: Domain persona, clear purpose, and scope.
- `[DOMAIN BOUNDARIES & REFUSALS]`: Explicit negative constraints (what it must refuse or refer to another specialist).
- `[EXECUTION PROTOCOL]`: Step-by-step operational reasoning (e.g., inspect/read ➔ plan ➔ verify ➔ execute).
- `[SAFETY & APPROVALS]`: Human-in-the-loop triggers for destructive, mutating, or production-facing actions.
- `[TOOL USAGE RULES]`: Guidance on tool invocation, parameter validation, and failure recovery.
- `[OUTPUT FORMAT]`: Standard output structure (checklists, markdown tables, structured JSON, code blocks).

## Order

1. Conduct Socratic Discovery with the human (or synthesize the answers if the brief is already comprehensive).
2. Formulate the agent details: `id` (kebab-case slug), `name`, `description`, `system_prompt` (structured using the Gold-Standard Blueprint), `tone`, `purpose`, `avatar_icon`, `model` (default `"default"` to inherit purpose slot model from Settings), and `show_in_chat` (default on). Never set `model` to a provider name like `"ollama"`.
3. For **each skill**, ask for `id`, optional name/description/body (order / pitfalls / done-when), **and which tools belong to that skill**. Tools are ids of **existing** platform callables. Do not invent Python modules. Do not put `.py` in the pack. A skill can have zero tools.
4. Write nested `skills: [{ "id": "...", "name": "...", "description": "...", "tools": ["tool_id", ...] }]`. Always put the tools inside the `tools` array of the skill they belong to. Derived `allowed_skill` is the skill ids. Derived `pack_tool_names` is the union of those tools.
5. Confirm `show_in_chat` (default on). Off means a behind-the-scenes specialist; Chat pickers hide them; handoff can still target them.
6. Optional: include CARD-123 workflow JSON (chapter list only). Do not copy transcripts, person facts, secrets, or `input_packet_json`.
7. Call `scaffold_agent_pack` with that nested spec, or `export_agent_pack` / `import_agent_pack` for an existing folder/zip.
8. Tell the human the agent id and render the post-creation confirmation with training guidance.

## Pitfalls

- Do not set `model` to provider names like `"ollama"` or `"gemini"`. Always use `"default"` so the agent inherits the user's configured purpose slot from Settings Purpose Matrix.
- Do not leave `skills[0].tools` empty while placing tools only at the top level. Always place the tools in the skill's `tools` array.
- Do not create a Pack Studio or a fourth primitive.
- Do not invent new skills or new tools in Agent Studio. Studio edits a pack that is already here.
- Do not ship new Python tool implementations in the zip. Factory Studio owns training and wiring new callables.
- Do not restripe Chat's picker: leave `show_in_chat` true unless the human asked to hide the specialist.
- Do not copy instance data. Workflows are the recipe, not this run's facts.
- Users do not hand-edit Python tool implementations in Agent Studio.
- Do not reship retired brochure seeds.
- If the human is ready to create a named agent with skills and existing tools, call scaffold_agent_pack. If a named tool is not in the catalog, say so and list real catalog tools (list_available_skills_and_tools). Do not propose_tool as part of pack birth. Do not propose_agent_specification for that walk.
- Never save_agent_specification to birth a pack. Approve-then-scaffold is the write.

## Done-when

- `$DATA_DIR/packs/<id>/pack.json` matches the nested schema in `docs/agent-packs.md` (`schema_version` 1.1, tools under skills)
- Skills exist under `$DATA_DIR/skills/<skill_id>/SKILL.md`
- The specialist appears in Agent Studio
- Pack-owned tool ids (union of skill tools) are ticked on; Show in Chat matches the spec
- Chat lists the agent only if Show in Chat is on
