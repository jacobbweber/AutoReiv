# CARD-413 — Ownership Audit & Recommended Architecture

> **Status**: Planning brief (Steps 1–3). **Not** an Accepted ADR.  
> **Card**: [CARD-413](../cards/CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md)  
> **Date**: 2026-09-21 (ET)  
> **Scope**: Docs / analysis only. No product code. No push / merge / tag.  
> **Audit tip**: `feat/card-413-storage-architecture-planning` @ `151e3703` (box checkout; Jarvis write unavailable in this executor).

---

## 0. Executive recommendation (one architecture)

**Recommend Hybrid C+** (refined Option C, not A/B/D):

| Layer | Canonical owner |
|-------|-----------------|
| **Mutable runtime registry** (agent profiles, overrides, tool bindings, settings, jobs/routines/sessions metadata) | **SQLite** (`database/autoreiv.db`) |
| **Cognitive memory** | **Per-agent** `packs/<id>/<snake>_memory.db` |
| **Domain / agent application storage** | **Per-agent** `packs/<id>/<snake>_storage.db` |
| **Wiki Markdown vault** | **Filesystem** at an **explicit** configured path (picker / reconnect; **no silent fallback**) |
| **Platform defaults** | **Repo** `platform-packs/` + `src/infrastructure/skills/seeds/` |
| **Pack interchange** | **Filesystem materialized on export/import only** — runtime does **not** treat AppData pack trees as silently re-seedable mirrors |

Reconciliation: stable `agent_id` + seed `version`/`content_hash` + **`user_modified`** (new). **Never** silent overwrite or prune of operator-touched content. Backup becomes a **manifest** enumerating DB(s), wiki URI, digests, and pack export set.

CARD-411: **defer / read-only** until an ADR Acceptance on this model.

---

## 1. Deep ownership audit (grounded in files / symbols)

### 1.1 Data root resolution & layout

**Primary module**: `src/infrastructure/data/resolver.py`

| Symbol / constant | Role |
|-------------------|------|
| `ENV_DATA_DIR` = `AUTOREIV_DATA_DIR` | Highest-priority root override |
| `ENV_DB_PATH` = `AUTOREIV_DB_PATH` | Explicit DB path (legacy `./data/autoreiv.db` strings → ignored → platform layout) |
| `ENV_WIKI_PATH` = `AUTOREIV_WIKI_PATH` | Explicit wiki path (legacy `./data/wiki` → ignored) |
| `ENV_BACKUP_DIR` = `AUTOREIV_BACKUP_DIR` | Backup directory override |
| `DATA_DIR_SETTING_KEY` = `data_dir` | Persisted SQLite setting (peeked from platform default DB or legacy checkout DB) |
| `BACKUP_DIR_SETTING_KEY` = `backup_dir` | Persisted backup dir |
| `DataDirResolver.platform_default` | Windows: `%LOCALAPPDATA%\AutoReiv`; POSIX: `~/.autoreiv`; Docker: `/data` |
| `DataDirResolver.resolve_root` | env → ctor setting → peeked SQLite → platform default |
| `DataDirResolver.resolve` | Builds `DataDirPaths`; **if root is checkout live tree → fall back to platform default** |
| `is_checkout_live_tree_path` / `ensure_live_data_root` | CARD-294 refuse: live packs/DBs/wiki must not live in git checkout (except `scratch/`) |
| `DataDirPaths` | `root`, `db_path`=`root/database/autoreiv.db`, `wiki_path`, `skills_path`, `agents_path`, `job_templates_path`, `packs_path`, `backups_path` |

**Canonical layout today (under resolved root)**:

```text
<root>/
  database/autoreiv.db          # operational SQLite
  wiki/                         # default vault (unless AUTOREIV_WIKI_PATH)
  skills/                       # bundled platform skill trees (seed-if-missing)
  agents/                       # legacy agent-adjacent FS (storage migrate sources)
  templates/jobs/
  packs/<agent_id>/             # live pack folders + per-agent DBs
    pack.json
    skills/...
    <snake>_storage.db
    <snake>_memory.db
  backups/
```

**Fragility**: Resolution peeks SQLite *before* the live store is opened; env vs setting vs default can diverge across processes. Checkout refuse is soft in `resolve()` (fallback) but hard in `ensure_live_data_root()` (raises).

---

### 1.2 Boot chain

```text
create_app (src/web/app.py)
  └─ bootstrap_data_dir(migrate=...)           # resolver.py
       ├─ DataDirResolver.resolve()
       ├─ ensure_layout()                      # mkdir root, db parent, wiki, skills, agents, templates, packs, backups
       ├─ migrate_if_needed()                  # legacy checkout DB/wiki copy; root autoreiv.db → database/
       ├─ seed_bundled_skill_packs(skills)     # seed.py — copy-if-missing SKILL.md
       ├─ seed_platform_pack_folders(packs)    # platform_packs.py — copytree if missing
       ├─ prune_bled_platform_skills(skills)   # delete known bled skill dirs
       └─ prune_orphan_databases(root)         # empty stray DBs only
  └─ set AUTOREIV_DB_PATH / AUTOREIV_WIKI_PATH
  └─ SQLiteStateStore.initialize_db()
  └─ BuiltinAgentRegistry.bootstrap(...)       # registry.py
       ├─ DeclarativePackReconciler.reconcile()  # purge RETIRED ids from DB + disk
       ├─ register tools / wiki / catalog...
       ├─ seed_bundled_skill_packs(skills)     # AGAIN
       └─ install_platform_agent_packs(data_root, registry, tools)
            ├─ DeclarativePackReconciler.reconcile()  # AGAIN
            ├─ cleanup_orphaned_platform_packs
            ├─ seed_platform_pack_folders      # AGAIN
            ├─ sync_checkout_example_user_packs
            ├─ for each PLATFORM pack:
            │    existing → SYNC prompt/skills/tools into SQLite + rewrite pack.json
            │              + copytree skills dirs_exist_ok + DELETE dest skills not in repo
            │    missing  → AgentPackService.import_path
            └─ discover user packs under packs/ → import or sync prompt from pack.json
```

**Platform pack IDs** (`DEFAULT_SEEDED_PACK_IDS`): `autoreiv`, `direct`, `developer`, `tutor`.  
**Retired** (purged on reconcile): `assistant`, `wiki`, `forge`, `homelab`, `homelab-admin`, `finance`.

---

### 1.3 Platform packs vs custom packs; pack.json vs SQLite dual-write

| Aspect | Platform (`origin=pack`, ids in `PLATFORM_PACK_IDS`) | Custom / user |
|--------|------------------------------------------------------|---------------|
| Seed | Repo `platform-packs/<id>/` → AppData `packs/<id>/` if missing | Forge / import / example sync from checkout `packs/` |
| Runtime profile | SQLite `custom_agents` (+ `agent_overrides`) | Same tables |
| FS projection | `packs/<id>/pack.json` + `skills/` | Same |
| Upgrade | **Aggressive sync**: repo prompt/skills/tools → SQLite **and** pack.json; skill dirs pruned to match repo | Prompt sync from *user* pack.json into SQLite; not re-seeded from platform-packs |
| Reconciler | Retired ids purged | Non-retired, non-desired preserved |

**Dual-write surfaces** (no single writer today):

1. `install_platform_agent_packs` writes `save_custom_agent_profile` / `save_agent_override` **and** rewrites `pack.json`.
2. `AgentPackService.export_folder` / `_persist_pack_manifest` materializes pack.json from profile.
3. User pack path: pack.json → SQLite on boot when prompt differs.
4. Forge / Settings APIs typically write SQLite first; FS may lag until export.

There is **no** `user_modified` / pack content-hash gate in pack sync code today (wiki notes have `content_hash` in frontmatter — packs do not).

---

### 1.4 Skills FS trees; overwrite / prune

| Tree | Seed | Upgrade behavior |
|------|------|------------------|
| `$DATA_DIR/skills/<id>/SKILL.md` | `seed_bundled_skill_packs` from `src/infrastructure/skills/seeds/` — **copy-if-missing only** | Safe for user edits; legacy `recommend-capability` dir deleted |
| `$DATA_DIR/packs/<platform_id>/skills/*` | Initial copytree; then on every boot for existing platform agents: `shutil.copytree(..., dirs_exist_ok=True)` then **`rmtree` any dest skill dir not in repo** | **High fragility** — operator-added skill folders under a platform pack are deleted |
| Bled skills in `$DATA_DIR/skills/` | `BLED_AGENT_SKILL_IDS` hard-delete list | Intentional cleanup; can surprise if operator renamed into those ids |

---

### 1.5 Tool bindings / `allowed_tools`

- Schema: `custom_agents.allowed_tools_json`, `agent_overrides.allowed_tools_json`, plus `pack_tools_json` / `allowed_skills_json` (`schema.py`).
- Platform sync merges: current SQLite tools ∪ user pack.json `allowed_tool_names` ∪ repo `pack_tool_names` ∪ `tools_for_platform_skills(...)`, then filters `RETIRED_TOOL_NAMES`.
- Runtime policy/chat reads registry profile (SQLite-backed), not pack.json directly.
- **Fragility**: Union-merge grows; retired filter helps but there is no “operator intentionally removed this tool” bit — reseed can **re-add** tools the operator removed from UI if they remain in repo seed.

---

### 1.6 Agent profiles (custom_agents, overrides, registry)

- `BuiltinAgentRegistry` holds in-memory profiles; persists via `SQLiteStateStore`.
- Tables: `custom_agents` (full profile), `agent_overrides` (per-id overlay fields including origin).
- Boot sync can rewrite **both** profile and override prompts/tools/skills from repo for platform ids.
- Stable id = folder name under `packs/<id>` = `custom_agents.id` (string PK). No separate UUID.

---

### 1.7 Settings persistence

- Table `settings(key, value_json, updated_at)`.
- Keys of interest: `data_dir`, `backup_dir`, `backup_schedule`, `backup_retention`, provider settings, purpose matrix / context window (CARD-412 OC-1).
- Settings Studio (`settings.js`) shows `wiki_path` as **read-only status** from `GET` data-dir paths — **no first-run picker / reconnect UX**.
- Wiki path itself is primarily env / resolver default, not a first-class durable “operator chose this vault” setting with migrate/reconnect flows comparable to `data_dir` migrate.

---

### 1.8 Per-agent storage.db vs memory.db + operational autoreiv.db

| DB | Path helper | Role |
|----|-------------|------|
| Operational | `database/autoreiv.db` | settings, agents, jobs, routines, sessions, telemetry, factory, credentials, … |
| Agent storage | `resolve_agent_storage_path` → `packs/<id>/<snake>_storage.db` | Domain application tables (e.g. finance); migrates legacy `storage.db` / `agents/<id>/` |
| Agent memory | `resolve_agent_memory_path` → `packs/<id>/<snake>_memory.db` | Cognitive brain (pinned / episodic / semantic); must not share storage path |

AGENTS.md already locks: storage ≠ memory; both under user data packs, never checkout.

**Note**: Operational DB still hosts some cognitive-looking tables historically (`episodic_facts` in schema.py) — topology clarification is part of C+.

---

### 1.9 Wiki path resolution, mkdir / fallback, Settings UI

| Step | Behavior |
|------|----------|
| Resolver | `AUTOREIV_WIKI_PATH` if non-legacy else `root/wiki` |
| `ensure_layout` | **`wiki_path.mkdir(parents=True, exist_ok=True)`** — silent create |
| `create_app` | Legacy wiki strings → use `data_paths.wiki_path`; sets `AUTOREIV_WIKI_PATH` |
| `WikiStore.__init__` | Same legacy fallback via `DataDirResolver` |
| `WikiStore.scaffold` | Ensures taxonomy dirs under chosen root; legacy folder migrate |
| Settings UI | Displays path text only (`settings.js` ~wikiEl) |
| Backup | If wiki outside data root, `_add_external_wiki` copies into zip under `wiki/` |

**Failure mode**: Configured path missing → mkdir elsewhere or empty vault appears “fine”; operator may get a **duplicate** empty wiki without realizing the intended vault was disconnected.

---

### 1.10 Import / export pack service

**Module**: `src/application/agent_packs/service.py` — `AgentPackService`

- `export_folder` / `export_zip`: profile → `pack.json` + copy allowed skills into `skills/`.
- `import_path`: zip or folder → `_import_folder` → SQLite profile + pack home under data dir.
- Fleet variants via `fleet.json`.
- Today runtime **also** depends on live AppData pack trees for skill bodies and platform sync — export is not merely interchange; live trees are part of the runtime brain.

---

### 1.11 Backup / restore

**Module**: `src/infrastructure/data/backup.py` — `DataDirBackupService`

- Zip walks data root (skips `.git`, venvs, `backups`); SQLite via consistent snapshot.
- External wiki inlined under archive `wiki/`.
- Restore: validate zip has `autoreiv.db`, pre-restore zip, replace tree (keeps `backups/` / `database/` handling special-cased).
- **Gaps vs target**: no manifest of wiki URI vs inlined content; per-agent DBs included only if under root walk; no provenance / hash list; restore of external wiki always lands under `root/wiki` shape inside archive — reconnect to original external path is not first-class.

---

### 1.12 Studios that touch storage ownership

| Studio | Touchpoints |
|--------|-------------|
| **Settings** | data root / backup / wiki path display; backup/restore APIs; provider + matrix settings in SQLite |
| **Forge** | custom agent CRUD → SQLite; pack export/import; skill/tool toggles; runbook edit (FS) — CARD-411 territory |
| **Wiki** | vault FS via WikiStore; inbox deliverables; templates |
| **Observe** | jobs/sessions/telemetry in operational DB; reports → wiki inbox |
| **Chat** | sessions/messages; agent profile tools/skills from registry; wiki tools; HITL approvals |
| **Factory / Skills** | capability manufacturing, skill trees, tool bindings (overlaps Forge — ownership ambiguity CARD-411) |
| **Routines** | routines/runs tables; may write wiki |

---

### 1.13 Failure modes (observed / structural)

| Mode | How it happens today | Blast radius |
|------|----------------------|--------------|
| **Orphan folder** | Pack dir on disk without `custom_agents` row | Boot may auto-import (user packs) or leave inert |
| **Orphan DB row** | Profile without pack folder | Runtime may lack skills FS; export rebuilds from profile + catalog |
| **Reseed overwrite** | Platform install sync rewrites prompt/pack.json; `copytree` skills | Operator edits to platform pack skills/prompts lost |
| **Skill prune** | Dest skill dirs not in repo deleted | Custom skills under platform pack id deleted |
| **Tool re-add** | Union merge reintroduces repo tools | Operator removals not sticky |
| **Missing wiki** | mkdir default / legacy fallback | Silent empty vault; wrong vault used |
| **Invalid refs** | Skill/tool names in SQLite not on disk / not registered | Chat lists tools that fail; capability index drift |
| **Retired purge** | Reconciler rmtree + delete profile | Correct for retired platform ids; dangerous if custom reused a retired id string |
| **Double seed/reconcile** | bootstrap + registry.bootstrap both seed/reconcile | Idempotent intent, but amplifies sync side effects |

---

## 2. Ownership map table

| Artifact | Canonical today | Projection / mirror | Writers | Readers | Upgrade behavior | Fragility | Recommended owner |
|----------|-----------------|---------------------|---------|---------|------------------|-----------|-------------------|
| Data root | Resolver (env > setting > default) | — | Settings migrate, env | All | Peek/migrate | Med (multi-source) | Keep resolver; single persisted `data_dir` |
| `autoreiv.db` | FS file under `database/` | — | State store, many services | Everyone | Schema migrate | Med (single blast) | **DB-canonical** operational registry |
| Platform pack profile | **Dual**: SQLite ≈ pack.json | pack.json + skills FS | install sync, Forge, import | Registry, Chat, Forge | Sync from repo overwrites | **High** | **SQLite registry**; pack.json export-only |
| Custom pack profile | SQLite + pack.json | pack.json | Forge, import | Registry | Soft sync from pack.json | Med | **SQLite**; FS interchange |
| Platform skill bodies | AppData pack skills FS (treated live) | Repo `platform-packs/*/skills` | install copytree/prune | Kernel, Forge | Overwrite + prune | **High** | Repo seed + DB/hash reconcile; export materializes |
| Bundled `$DATA_DIR/skills` | FS seed-if-missing | Repo seeds/ | seed.py | UserSkillCatalog | Safe copy-if-missing | Low | Keep FS seed-if-missing **or** fold into export model |
| Tool bindings | SQLite JSON (+ pack.json fields) | pack.json | sync, Forge | Policy, Chat | Union merge | Med-High | **SQLite only**; export projects |
| Agent overrides | SQLite `agent_overrides` | — | sync, Settings/Forge | Registry merge | Sync can clobber | High | SQLite; respect `user_modified` |
| Settings | SQLite `settings` | — | Settings API | Resolver, studios | Durable | Low | Keep SQLite |
| Jobs / routines / sessions | SQLite operational | — | Orchestration | Observe, Chat | Migrate with DB | Med | Keep in operational storage DB |
| Per-agent storage | `*_storage.db` | — | Domain tools | Agent domain | Path migrate helpers | Low | Keep FS-side DB; DB-canonical content |
| Per-agent memory | `*_memory.db` | — | Memory repos | Chat, education | Separate path enforced | Low | Keep separate cognitive DB |
| Wiki Markdown | FS vault | Optional zip `wiki/` | WikiStore, tools | RAG, Wiki Studio | mkdir + legacy fallback | **High** (path UX) | **FS-canonical**; explicit path setting |
| Wiki meta/hash | Frontmatter `content_hash` | — | WikiStore | Curator, RAG | Already hashed | Low | Keep; model for packs |
| Backups | Zip tree | External wiki inlined | BackupService | Restore | No manifest | Med | **Manifest** + DB snapshot + wiki policy |
| Pack export zip | Materialized FS | — | AgentPackService | Import | Round-trip partial | Med | Interchange only; not runtime dependency |
| Repo `platform-packs/` | **Repo-canonical seed** | — | Humans / cards | Seeder | Source of defaults | Low (if not treated live) | Repo-canonical defaults |

---

## 3. Intent synthesis (steering + product reality)

From `steering/product.md`, `tech.md`, `structure.md`, `AGENTS.md`, checkout-hygiene, and operator-contract testing:

1. **Local-first**: user data, SQLite, and markdown vaults live on the operator’s machine — never in the git checkout.
2. **Operator-owned**: Studios are the human levers (Settings, Forge, Wiki, Observe, Chat). Upgrades must not trash operator work.
3. **Studio-driven**: durable outcomes (settings stick, wiki notes exist, reports land in inbox) are the proof bar (ADR-0055 / OC-*).
4. **Packs / skills as capabilities**: Pack = packaging of one agent; Skill = one `SKILL.md` runbook; Tool = one callable. Platform ≠ Global naming.
5. **Wiki as human documents**: Markdown vault is for humans and agents to read/write notes — not a dump of agent registry JSON.
6. **Upgrade safety**: seed/reconcile must be idempotent; second boot = no churn; no silent overwrite/fallback.

These intents **reject** treating AppData pack trees as disposable mirrors of the repo, and **reject** silent wiki mkdir as a substitute for configuration.

---

## 4. ONE recommended architecture — Hybrid C+

### 4.1 What is canonical where

| Concern | Canonical | Not canonical |
|---------|-----------|---------------|
| Agent profile, overrides, tool/skill bindings, show_in_chat, origin | **Operational SQLite** | Live pack.json (becomes export projection) |
| Settings, jobs, routines, sessions, approvals, telemetry, factory meta | **Operational SQLite** (`storage` role) | — |
| Cognitive memory | **Per-agent memory.db** | Must not share storage.db |
| Agent domain tables | **Per-agent storage.db** | — |
| Wiki note bodies & templates | **Filesystem vault** at configured path | DB blobs for note bodies |
| Platform defaults (prompts, stock skills, stock tools) | **Repo** `platform-packs/` + skill seeds | AppData copies as “source of truth” |
| Portable packs | **Export/import artifacts** (folder/zip) | Runtime requiring those trees to stay in sync with repo |

### 4.2 Reconciliation rules

For each platform artifact keyed by **stable id** (`agent_id`, skill id, tool name):

1. Record seed provenance: `seed_id`, `seed_version` and/or `content_hash` of last applied repo revision.
2. Set **`user_modified=true`** when operator (or Forge/Factory) changes profile/skills/bindings away from last applied seed hash.
3. On boot / upgrade:
   - If not `user_modified` and seed hash differs → apply seed update (idempotent).
   - If `user_modified` → **never** overwrite; optionally surface “upstream update available” in Forge/Settings.
   - **Never** delete skill dirs solely because repo omitted them when `user_modified` or when skill id is not in the retired list.
4. Retired platform ids: keep explicit purge list (today’s reconciler) but never reuse those ids for custom agents without a rename gate.
5. Tool bindings: SQLite is sole writer; export materializes `allowed_tool_names`. Removals stick; seed may propose adds only when not `user_modified` (or via explicit “accept upstream” action).

### 4.3 Storage vs memory DB topology

**Recommend (default)**:

- Keep **one** platform operational DB: `database/autoreiv.db` (registry + ops) — do **not** split platform into two files in v1 of migration (avoids dual-open complexity).
- Keep **per-agent** `*_storage.db` and `*_memory.db` as today.
- Document naming: operational DB = “storage role” at platform level; memory remains cognitive-only.
- Migration follow-up (optional later): move any cognitive tables still living in `autoreiv.db` into per-agent memory or a dedicated platform memory DB — **out of ADR v1** unless Jacob picks fork #3 “split platform memory”.

### 4.4 Interchange

- **Export** materializes `pack.json` + skills folders/zips from SQLite + skill store.
- **Import** writes SQLite registry + stores skill bodies in a controlled skill store (FS under pack home is fine as *store*, not as *repo mirror*).
- Runtime boot **must not** depend on re-copying from `platform-packs/` except for first install of missing ids and hash-gated updates.
- Round-trip fidelity required: skills + tool bindings + stable ids (feeds OC-S2).

### 4.5 Wiki: first-run picker + no silent fallback + migrate/reconnect

1. First run / empty config: **folder picker** (suggest under data root, Documents, or OneDrive — product fork).
2. Persist chosen path as durable setting (e.g. `wiki_path`) distinct from env override.
3. If configured path missing/unreadable: **fail visibly** + “Reconnect / Migrate” actions — **no** silent mkdir of a different default vault.
4. `ensure_layout` must **not** create wiki at a fallback path when a configured path is set but missing.
5. Migrate/reconnect: copy or repoint; verify with OC-S5 / OC-S6.
6. Settings Studio: editable path + status (exists / missing / external) — not read-only text only.

### 4.6 Manifest backup / restore

Backup zip (or sidecar JSON) includes:

```json
{
  "schema_version": 1,
  "created_at": "...",
  "data_root": "...",
  "databases": [
    {"role": "operational", "path": "database/autoreiv.db", "sha256": "..."},
    {"role": "agent_storage", "agent_id": "...", "path": "packs/.../x_storage.db", "sha256": "..."},
    {"role": "agent_memory", "agent_id": "...", "path": "packs/.../x_memory.db", "sha256": "..."}
  ],
  "wiki": {
    "configured_uri": "file:///...",
    "include_content": true,
    "content_digest": "...",
    "archive_prefix": "wiki/"
  },
  "packs_export_set": ["autoreiv", "developer", "..."],
  "provenance": {"app_version": "...", "card": "CARD-413"}
}
```

Restore validates manifest, restores DBs, restores or rebinds wiki per policy (fork #5), never invents a second vault silently.

### 4.7 Why reject A / B / D (short)

| Option | Why not primary |
|--------|-----------------|
| **A Harden-only FS-first** | Leaves dual canonical truth (SQLite + pack.json + live skill mirrors). Hardening hashes helps but Studios already treat SQLite as the profile brain; FS-first fights the product. Prune/overwrite bugs are structural to “AppData is a mirror.” |
| **B One SQLite for almost everything** | Puts wiki bodies and large skill markdown into DB — hurts human editability, git-friendly vault workflows, and blast radius. Conflicts with “wiki as human documents.” |
| **D CAS + DB index** | Strongest integrity/rollback, but highest migration and UX cost for a local-first single-operator product now. Can be a **later** evolution under the same C+ ownership rules; not the first cutover. |

C+ keeps human FS where humans work (wiki + exports), DB where the control plane already lives, and repo where defaults belong.

---

## 5. Product-policy forks for Jacob (max 6) — recommended defaults

Do **not** treat these as interviewed answers; defaults are auditor recommendations for the parent walkthrough.

| # | Fork | Recommended default | Why |
|---|------|---------------------|-----|
| 1 | **Skills editing** | UI/Forge-Factory is primary editor; **files remain readable** under pack skill store; advanced operators may edit files but that sets `user_modified` | Matches Studio-driven product; avoids silent clobber; still local-first |
| 2 | **Built-in customization** | **Layered overlay** (overrides table) + explicit **“Fork to custom pack”** when divergence is large; no silent in-place clobber of seed | Preserves upgrade path for untouched builtins |
| 3 | **DB topology** | Keep **one** operational `autoreiv.db` + per-agent storage/memory DBs | Least migration risk; already matches AGENTS.md |
| 4 | **Wiki first-run path** | Picker with **suggestion = `<data_root>/wiki`**; allow Documents/OneDrive | Predictable default + operator choice |
| 5 | **Backup includes wiki?** | **Opt-in include content** + always store **configured URI** in manifest | Large vaults / external OneDrive; avoid surprise huge zips |
| 6 | **Missing wiki path** | **Fail visibly** + reconnect/migrate only — **never** silent recreate elsewhere | Prevents duplicate vaults and false “empty wiki” |

*(Export fidelity = yes round-trip; migration = forward-only with backup restore — fold into ADR text rather than extra forks.)*

---

## 6. Phased migration sketch (future build card; plan now)

1. **This card** — audit + recommendation (done in this brief); Jacob `continue` / forks.
2. ADR **Proposed** → walkthrough → **Accepted** (only with Jacob OK). Link from CARD-413; set `adr:`.
3. Additive schema: provenance + `user_modified` + optional `wiki_path` setting; **dual-read validation** (compare pack.json vs SQLite; report drift) — avoid unbounded dual-write.
4. Stop destructive platform skill prune / prompt overwrite behind feature flag; hash-gated apply.
5. Wiki picker + fail-visible path; Settings UX.
6. Manifest backup write path (additive); restore dry-run.
7. Migration dry-run report on live/temp user-data.
8. Backup → execute migration → verification **OC-S1..S6**.
9. Cutover: SQLite single writer for profiles/bindings; pack.json export projection.
10. Prune obsolete seed-as-live assumptions; rollback drill = restore pre-cutover zip + manifest.

**Dual-write**: only if explicitly bounded with kill switch and comparison metrics — not the default plan.

---

## 7. Operator contracts still required (OC-S1..S6)

| ID | Contract |
|----|----------|
| OC-S1 | Built-in reconcile idempotent; user edits survive second boot |
| OC-S2 | Pack export → import fidelity (skills, tool bindings, stable IDs) |
| OC-S3 | Backup/restore restores DB(s), wiki path/policy, content, manifest |
| OC-S4 | Upgrade migration preserves agents/skills/bindings; no invalid refs |
| OC-S5 | Configured wiki path persists; missing path fails visibly; migrate + rollback verified |
| OC-S6 | Fresh install first-run folder picker; no duplicate fallback wiki |

Proof home: `tests/integration/operator_contracts/` (or successor), real temp user-data — per ADR-0055.

---

## 8. CARD-411 implication

**Confirm: defer / read-only until CARD-413 ADR is Accepted.**

- CARD-411 (runbook YAML frontmatter, tool binding UI, Forge vs Factory) must target the **single** canonical binding store.
- Under C+: editors write **SQLite** (+ skill body store); export projects files. Forge = RBAC/assignment; Factory = capability workshop — final UX split still CARD-411’s job, but **not** on dual-write FS+DB.
- Keep CARD-411 **Ready** but **blocked** on ADR outcome; allow read-only inspector work only if explicitly narrowed on both cards after Jacob OK.

---

## 9. Options A–D scorecard (summary)

| Criterion | A Harden FS | B One DB | **C+ Hybrid** | D CAS |
|-----------|-------------|----------|---------------|-------|
| Upgrade idempotence | Med | High | **High** | High |
| User editability | High (files) | Low for wiki/skills | **High** (wiki FS + Studio) | Med |
| Export fidelity | Med | High | **High** | High |
| Blast radius | Med | **Worse** (one DB) | **Good** | Good |
| Migration cost | Low | High | **Med** | **Highest** |
| Observability | Med | High | **High** | Highest |
| Local-first / operator-owned | Med | Med | **Best fit** | Med |
| Concurrency | Med | SQLite lock risk | **Acceptable** | Med |

**Selected: C+.**

---

## 10. Key code citations (audit anchors)

- `src/infrastructure/data/resolver.py` — `DataDirResolver`, `bootstrap_data_dir`, `ensure_layout`, `ensure_live_data_root`, `resolve_agent_storage_path`, `resolve_agent_memory_path`, prune helpers
- `src/infrastructure/data/backup.py` — `DataDirBackupService`, `_add_external_wiki`
- `src/infrastructure/data/migrate.py` — data-dir relocate
- `src/infrastructure/skills/platform_packs.py` — `seed_platform_pack_folders`, `install_platform_agent_packs` (sync + skill prune)
- `src/infrastructure/skills/reconciler.py` — `DeclarativePackReconciler`
- `src/infrastructure/skills/seed.py` — `seed_bundled_skill_packs`
- `src/infrastructure/agents/registry.py` — `BuiltinAgentRegistry.bootstrap`
- `src/infrastructure/memory/schema.py` — `settings`, `custom_agents`, `agent_overrides`, jobs/routines/sessions
- `src/application/agent_packs/service.py` — export/import
- `src/domain/wiki/store.py` — root resolution / scaffold
- `src/web/app.py` — `create_app` → bootstrap
- `src/web/static/modules/studios/settings.js` — wiki_path display
- `platform-packs/` — repo seed (`autoreiv`, `direct`, `developer`, `tutor`)
- `.agents/rules/checkout-hygiene.md` — no live data in checkout

---

## 11. Out of scope (this brief)

- No product implementation, mass AppData deletion, or Accepted ADR.
- No push / merge / tag.
- No CARD-411 implementation.

---

*End of CARD-413 Steps 1–3 brief.*
