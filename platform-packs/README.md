# Platform Agent Packs

These two specialists **always install**. They ship with AutoReiv.

| Pack | Chat | Job |
| --- | --- | --- |
| `assistant/` | on | Day-to-day assistant. Weekly/daily task loop. |
| `autoreiv/` | on | Platform SRE, pack scaffold/import/export, HITL recommend when stuck. |

On launch, if `$DATA_DIR/packs/assistant` or `$DATA_DIR/packs/autoreiv` is missing, AutoReiv copies the matching folder from here. An existing folder is never overwritten.

This is **not** the optional catalog. User specialists (Conductor, Coding, Review, and packs you add) live in repo-root `agent-packs/` and are **not** scanned on startup.

Wiki is a **Platform skill** (any agent can tick it), not a pack. Assistant and AutoReiv seed with `wiki` ticked.

Name is Platform, not Global.
