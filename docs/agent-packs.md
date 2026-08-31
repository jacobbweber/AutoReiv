# Agent Packs

An Agent Pack is packaging, not a fourth primitive. The primitives stay **agent**, **skill** (one `SKILL.md` runbook), and **tool** (one atomic callable). A pack is one specialist in a folder you can import, export, or back up.

This how-to is the SDK: folder layout, JSON fields, hand import, and hand export. Agent Studio Import / Export and AutoReiv's pack tools write the same schema.

## Folder layout

```
<pack-id>/
  pack.json
  skills/<skill_id>/SKILL.md
  workflows/<workflow_id>.json
```

- `pack.json` is identity plus allowlists and Show in Chat.
- `skills/` holds one `SKILL.md` per `allowed_skill` id (name + blurb in frontmatter, body is the runbook).
- `workflows/` holds CARD-123 recipe JSON already used at `$DATA_DIR/agents/<id>/workflows/`.
- Do **not** include transcripts, person facts, secrets, `input_packet_json`, or Python tool implementations. `pack_tool_names` are ids of callables that already exist on the platform.

A zip of that folder (with `pack.json` at the zip root, or inside one top-level folder) is the portable form.

## pack.json fields

| Field | Type | Notes |
| --- | --- | --- |
| `schema_version` | string | `1.0` |
| `id` | string | Agent slug (letters, digits, hyphen) |
| `name` | string | Display name |
| `description` | string | One-line role |
| `system_prompt` | string | Instructions |
| `tone` | string | Studio tone preset |
| `purpose` | string | Purpose Matrix slot |
| `avatar_icon` | string | Studio avatar id |
| `model` | string | Model override or `default` |
| `allowed_skill` | string[] | SKILL.md ids in `skills/` |
| `pack_tool_names` | string[] | Existing platform tool ids owned by this pack |
| `show_in_chat` | bool | Default `true`. Off hides the agent from Chat pickers only |
| `created_at` | string or null | ISO timestamp |
| `updated_at` | string or null | ISO timestamp |

Show in Chat off still allows handoff to that agent. Building or importing a pack does not hide anyone else.

## Hand export

1. In Agent Studio, select the specialist and click **Export**. That writes `$DATA_DIR/packs/<id>/` and downloads `<id>.zip`.
2. Or copy the folder yourself: identity from the agent, each ticked runbook from `$DATA_DIR/skills/<skill_id>/SKILL.md`, workflows from `$DATA_DIR/agents/<id>/workflows/*.json`. Skip chat transcripts and SQLite facts.

## Hand import

1. In Agent Studio, click **Import** and choose the zip.
2. Or unzip into `$DATA_DIR/packs/<id>/` and ask AutoReiv to import that path.
3. Import creates or updates the custom agent, copies `SKILL.md` files into `$DATA_DIR/skills/`, copies workflows onto that agent, unions `pack_tool_names` into `allowed_tool_names` (those ticks come on), and sets Show in Chat from `pack.json`.

The agent appears in Agent Studio after import. Chat's agent dropdown lists it only when Show in Chat is on.

## Core roster intent

Shipped core stays Assistant + AutoReiv. Specialists arrive as packs later. Existing builtins are not removed by this format.
