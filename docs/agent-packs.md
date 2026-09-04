# Agent Packs

Assistant and AutoReiv are **Platform Agent Packs** in repo-root `platform-packs/`. They always copy into `$DATA_DIR/packs/` on launch if missing. `agent-packs/` remains the optional catalog and is **not** scanned on startup.

An Agent Pack is packaging, not a fourth primitive. The primitives stay **agent**, **skill** (one `SKILL.md` runbook), and **tool** (one atomic callable). A pack is one specialist in a folder you can import, export, or back up.

This how-to is the SDK: folder layout, JSON fields, hand import, and hand export. Agent Studio Import / Export and AutoReiv's pack tools write the same schema. Two authors, one landing place (`$DATA_DIR/packs/<id>/` plus the agent, skills, and workflows the platform already loads).

An agent has many skills. Each skill has tools. Skills belong to one agent. Agent Studio edits a pack that is already here (name, instructions, tone, Show in Chat, ticks, Import/Export). It is not where you invent new skills or new tools.

## Folder layout

```
<pack-id>/
  pack.json
  skills/<skill_id>/SKILL.md
  workflows/<workflow_id>.json
```

- `pack.json` is identity, nested skills (tools under each skill), derived allowlists, and Show in Chat.
- `skills/` holds one `SKILL.md` per skill id (name + blurb in frontmatter, body is the runbook).
- `workflows/` holds CARD-123 recipe JSON already used at `$DATA_DIR/agents/<id>/workflows/`.
- Do **not** include transcripts, person facts, secrets, `input_packet_json`, or Python tool implementations. Tool ids under each skill are callables that already exist on the platform.

A zip of that folder (with `pack.json` at the zip root, or inside one top-level folder) is the portable form.

## pack.json fields

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | string | `1.1` (`1.0` sibling lists still import) |
| `id` | string | Agent slug (letters, digits, hyphen) |
| `name` | string | Display name |
| `description` | string | One-line role |
| `system_prompt` | string | Instructions |
| `tone` | string | Studio tone preset |
| `provider` | string | Explicit LLM provider or `default` |
| `avatar_icon` | string | Studio avatar id |
| `model` | string | Model override or `default` |
| `skills` | object[] | Nested authoring shape: `{ id, tools, name?, description? }` |
| `allowed_skill` | string[] | Derived: skill ids. Kept for 1.0 compat |
| `pack_tool_names` | string[] | Derived: union of `skills[].tools` plus leftover top-level ids |
| `show_in_chat` | bool | Default `true`. Off hides the agent from Chat pickers only |
| `created_at` | string or null | ISO timestamp |
| `updated_at` | string or null | ISO timestamp |

Show in Chat off still allows handoff to that agent. Building or importing a pack does not hide anyone else.

### Nested example

```json
{
  "schema_version": "1.1",
  "id": "eu-c-specialist",
  "name": "EUC Specialist",
  "description": "Endpoint specialist",
  "system_prompt": "You help with endpoint tasks.",
  "tone": "technical",
  "provider": "default",
  "avatar_icon": "cpu",
  "model": "default",
  "skills": [
    { "id": "user-provisioning", "name": "User provisioning", "tools": ["system_info"] },
    { "id": "endpoint-audit", "name": "Endpoint audit", "tools": [] }
  ],
  "allowed_skill": ["user-provisioning", "endpoint-audit"],
  "pack_tool_names": ["system_info"],
  "show_in_chat": true
}
```

On load/import, skill ids become `allowed_skill` and the union of skill tools becomes `pack_tool_names` (those ticks come on). A 1.0 pack that only has sibling `allowed_skill` + `pack_tool_names` still imports. Export of a live agent that has no per-skill map writes `skills: [{ "id": "...", "tools": [] }, ...]` plus top-level `pack_tool_names` so import still ticks tools. It does not copy the same tool list onto every skill.

## Two authors, one schema

1. **Talk to AutoReiv** (platform agent in Chat): runbook `build-agent-pack` plus pack tools. AutoReiv asks for agent details, each skill, and which tools belong to that skill, then writes this nested pack. Agent Studio **New Agent** switches to Chat, selects AutoReiv, starts a fresh session, and fills `I am ready to create a new agent.` so you hit Send. It does not save a blank custom agent.
2. **Hand SDK + Import/Export**: same `pack.json` folder/zip. This page is the how-to. Agent Studio Import/Export on the selected agent is the GUI for a pack that is already here.

Both land in the same data-dir location so the platform loads them the same way.

## Hand export

1. In Agent Studio, select the specialist and click **Export**. That writes `$DATA_DIR/packs/<id>/` and downloads `<id>.zip`.
2. Or copy the folder yourself: identity from the agent, each ticked runbook from `$DATA_DIR/skills/<skill_id>/SKILL.md`, workflows from `$DATA_DIR/agents/<id>/workflows/*.json`. Skip chat transcripts and SQLite facts.

## Hand import

1. In Agent Studio, click **Import** and choose the zip.
2. Or unzip into `$DATA_DIR/packs/<id>/` and ask AutoReiv to import that path.
3. Import creates or updates the custom agent, copies `SKILL.md` files into `$DATA_DIR/skills/`, copies workflows onto that agent, unions mapped tools into `pack_tool_names` / `allowed_tool_names` (those ticks come on), and sets Show in Chat from `pack.json`.

The agent appears in Agent Studio after import. Chat's agent dropdown lists it only when Show in Chat is on.

## Repo catalog (optional)

`agent-packs/` in the git checkout is an optional catalog. The app does **not** auto-load it on startup. Import is explicit: Agent Studio Import or AutoReiv `import_agent_pack`. A fresh AutoReiv is Assistant + AutoReiv until you import. Shipped catalog packs are Conductor, Coding, and Review (one agent each). AutoReiv `scaffold_agent_pack` still writes `$DATA_DIR/packs/`. Packs that belong in git are copied into `agent-packs/`.

## Core roster intent

Shipped core is Assistant + AutoReiv. Agent Builder stays a hidden builtin (Chat and Agent Studio skip `agent-builder` by id). Conductor, Coding, and Review are Agent Packs, not builtins.
