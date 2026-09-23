# Platform Agent Packs

These four specialists **always install**. They ship with AutoReiv.

| Pack | id + display | Chat | Job |
| --- | --- | --- | --- |
| `autoreiv/` | `autoreiv` / AutoReiv | on | Primary companion, platform SRE, pack scaffold/import/export, wiki and daily tasks. |
| `direct/` | `direct` / Direct | on | Zero-tool direct chat. Direct mounts no tools. |
| `developer/` | `developer` / Developer | on | Platform software engineer (full SDLC) plus scaffold, improve, and build for agents, skills, and tools. **Keep id+display `developer`.** Legacy `coding` / `coder` ids are obsolete and are not platform seeds. |
| `tutor/` | `tutor` / Tutor | on | Socratic tutor grounded in the learner's wiki notes. |

Seeded ids match `DEFAULT_SEEDED_PACK_IDS`: `autoreiv`, `direct`, `developer`, `tutor`.

On launch, if `$DATA_DIR/packs/<id>` is missing for any of the four, AutoReiv copies the matching folder from here. An existing folder is never overwritten when the profile is `user_modified` (user copies stay). Homelab and other user specialists are **not** platform seeds — import them into `$DATA_DIR/packs/` (via `AUTOREIV_DATA_DIR`) only.

Wiki is a **Platform skill** (any agent can tick it), not a pack.

Name is Platform, not Global. There is no second in-repo catalog folder (`agent-packs/` removed); user packs come from user-data import only. The hidden `agent-builder` builtin is retired. Developer holds its still-useful propose, commit, and scaffold tools.
