---
name: Build Agent Pack
description: Write, import, and export one specialist Agent Pack matching the platform schema.
---

# Build Agent Pack

Use this runbook when the human wants a specialist packaged, imported, or exported. An Agent Pack is packaging, not a fourth primitive. Primitives stay agent, skill (one SKILL.md), and tool (one callable).

An agent has many skills. Each skill has tools. Skills belong to one agent. Ask for that shape, then write the nested pack.

## Tools

- `scaffold_agent_pack` - write a pack from a structured spec and import it
- `export_agent_pack` - export an existing agent id to a folder + zip under the data dir
- `import_agent_pack` - import a folder or zip path into user data

## Order

1. Confirm agent details: `id`, `name`, `description`, `system_prompt`, `tone`, `purpose`, `avatar_icon`, `model`, and `show_in_chat` (default on).
2. For **each skill**, ask for `id`, optional name/description/body (order / pitfalls / done-when), **and which tools belong to that skill**. Tools are ids of **existing** platform callables. Do not invent Python modules. Do not put `.py` in the pack. A skill can have zero tools.
3. Write nested `skills: [{ "id": "...", "tools": ["tool_id", ...] }]`. Derived `allowed_skill` is the skill ids. Derived `pack_tool_names` is the union of those tools (plus any leftover top-level list). Do not copy the same tool list onto every skill.
4. Confirm `show_in_chat` (default on). Off means a behind-the-scenes specialist; Chat pickers hide them; handoff can still target them.
5. Optional: include CARD-123 workflow JSON (chapter list only). Do not copy transcripts, person facts, secrets, or `input_packet_json`.
6. Call `scaffold_agent_pack` with that nested spec, or `export_agent_pack` / `import_agent_pack` for an existing folder/zip.
7. Tell the human the agent id and whether it will show in Chat.

## Pitfalls

- Do not create a Pack Studio or a fourth primitive.
- Do not invent new skills or new tools in Agent Studio. Studio edits a pack that is already here.
- Do not ship new Python tool implementations in the zip. Later builder owns wiring new callables.
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
