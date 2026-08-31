# Agent Packs (optional catalog)

These folders are **optional specialists**, not shipped core.

Assistant and AutoReiv are Platform Agent Packs in repo-root `platform-packs/` (always installed). This directory is the **optional** user catalog. This directory is a repo catalog. The app does **not** scan it on startup.

## Import

- Agent Studio: select **Import** and choose the pack zip/folder.
- Or ask AutoReiv to run `import_agent_pack` on a path such as `agent-packs/conductor`.

Imported packs land in `$DATA_DIR/packs/<id>/` and appear in Agent Studio. Chat lists a pack only when Show in Chat is on.

Shipped in this catalog:

| Pack | Chat | Job |
| --- | --- | --- |
| `conductor/` | on | Covision. Writes cards/specs. Hands one Ready card to Coding. |
| `coding/` | off | One Ready card, implement, conventional commit if a repo exists, In Review, stop. |
| `review/` | off | Judge Coding. Concrete fix list. Handoff to Coding or Conductor. Never writes product files. |

Handoff ids stay `conductor`, `coding`, and `review`.

See `docs/agent-packs.md` for the pack schema.
