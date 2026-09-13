# Platform Agent Packs

These three specialists **always install**. They ship with AutoReiv.

| Pack | id + display | Chat | Job |
| --- | --- | --- | --- |
| `assistant/` | `assistant` / Assistant | on | Day-to-day assistant. Weekly/daily task loop. |
| `autoreiv/` | `autoreiv` / AutoReiv | on | Platform SRE, pack scaffold/import/export, HITL recommend when stuck. |
| `developer/` | `developer` / Developer | on | Platform software engineer (full SDLC). **Keep id+display `developer`.** Legacy `coding` / `coder` ids are obsolete and are not platform seeds. |

On launch, if `$DATA_DIR/packs/<id>` is missing for any of the three, AutoReiv copies the matching folder from here. An existing folder is never overwritten (user copies stay). Homelab and other user specialists are **not** platform seeds — import them into `$DATA_DIR/packs/` (via `AUTOREIV_DATA_DIR`) only.

Wiki is a **Platform skill** (any agent can tick it), not a pack. Assistant and AutoReiv seed with `wiki` ticked.

Name is Platform, not Global. There is no second in-repo catalog folder (`agent-packs/` removed); user packs come from user-data import only.
