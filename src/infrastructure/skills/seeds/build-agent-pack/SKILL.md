---
name: Build Agent Pack
description: Write, import, and export one specialist Agent Pack matching the platform schema.
---

# Build Agent Pack

Use this runbook when the human wants a specialist packaged, imported, or exported. An Agent Pack is packaging, not a fourth primitive. Primitives stay agent, skill (one SKILL.md), and tool (one callable).

## Tools

- `scaffold_agent_pack` — write a pack from a structured spec and import it
- `export_agent_pack` — export an existing agent id to a folder + zip under the data dir
- `import_agent_pack` — import a folder or zip path into user data

## Order

1. Confirm identity: `id`, `name`, `description`, `system_prompt`, `tone`, `purpose`, `avatar_icon`, `model`.
2. Confirm `allowed_skill` (runbook ids) and optional skill bodies (name, blurb, order / pitfalls / done-when).
3. Confirm `pack_tool_names` as ids of **existing** platform callables. Do not invent Python modules. Do not put `.py` in the pack.
4. Confirm `show_in_chat` (default on). Off means a behind-the-scenes specialist; Chat pickers hide them; handoff can still target them.
5. Optional: include CARD-123 workflow JSON (chapter list only). Do not copy transcripts, person facts, secrets, or `input_packet_json`.
6. Call `scaffold_agent_pack` with that spec, or `export_agent_pack` / `import_agent_pack` for an existing folder/zip.
7. Tell the human the agent id and whether it will show in Chat.

## Pitfalls

- Do not create a Pack Studio or a fourth primitive.
- Do not ship new Python tool implementations in the zip. Later builder owns wiring new callables.
- Do not restripe Chat's picker: leave `show_in_chat` true unless the human asked to hide the specialist.
- Do not copy instance data. Workflows are the recipe, not this run's facts.
- Users do not hand-edit Python tool implementations in Agent Studio.
- Do not reship retired brochure seeds.

## Done-when

- `$DATA_DIR/packs/<id>/pack.json` matches the schema in `docs/agent-packs.md`
- Skills exist under `$DATA_DIR/skills/<skill_id>/SKILL.md`
- The specialist appears in Agent Studio
- Pack-owned tool ids are ticked on; Show in Chat matches the spec
- Chat lists the agent only if Show in Chat is on
