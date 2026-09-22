---
id: CARD-413
title: "Durable Runtime Registry, Platform Reconciliation, Portable Pack Interchange, and Configurable Wiki Root"
status: Ready
created: 2026-09-21
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:architecture
  - type:planning
  - area:storage
  - area:packs
  - area:wiki
  - area:data-dir
---

# [CARD-413] Durable Runtime Registry, Platform Reconciliation, Portable Pack Interchange, and Configurable Wiki Root

> **Status**: Ready (planning / decision only — **no implementation on this card**)
> **Created**: 2026-09-21
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md) (**Proposed** — Accept pending Jacob)
> **Labels**: `type:architecture`, `type:planning`, `area:storage`, `area:packs`, `area:wiki`, `area:data-dir`
> **Branch**: `feat/card-413-storage-architecture-planning` (docs-only; do not push)

---

## Gate language (exact reply phrases)

This card **requires a decision/design phase before build**.

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Discuss, refine inventory, compare options, draft ADR language — **still no product code** |
| **`build`** | Only after an ADR is **Accepted** and the migration plan in this card (or successor) is approved |
| **`merge to qa`** | Only after In Review + live operator test of the eventual build card(s) |

Do **not** treat scaffolding this Ready card as approval to implement.

---

## 1. Four Beats

### Beat 1 — What Jacob means

Agent packs and skills as **raw files seeded/deployed into AppData** have caused:

- change / reseed / upgrade fragility
- invalid DB references after folder churn
- unclear ownership (repo seed vs AppData copy vs SQLite profile)
- silent overwrite / prune of operator edits
- wiki path ambiguity (default under data root vs relocated vault; no first-run picker; risk of duplicate fallbacks)

Jacob wants a **methodical ownership discussion and analysis** before any major change. The working **hypothesis** (not a decision) is:

- **Database-backed** mutable runtime registry (agents, bindings, settings, jobs/sessions metadata)
- **Filesystem-backed** wiki + pack interchange (export/import artifacts humans can open)
- **Repo-canonical** platform defaults with **versioned / hash / user_modified** reconciliation (no silent clobber)
- Separate **`storage.db`** (domain/ops) vs **`memory.db`** (cognitive) — already partially true per agent; clarify platform-level split
- **Manifest-based** backup/restore (DB(s) + wiki path + content + provenance)
- Wiki: first-run **local folder picker**, explicit reconnect/migrate; **never silent fallback**

### Beat 2 — What AutoReiv does now (grounded inventory)

Live user data root (not the git checkout):

| Platform | Default root |
|----------|----------------|
| Windows | `%LOCALAPPDATA%\AutoReiv` (`DataDirResolver.platform_default`) |
| POSIX | `~/.autoreiv` |
| Docker | `/data` |

Resolution order (`src/infrastructure/data/resolver.py`):

1. `AUTOREIV_DATA_DIR` env
2. Persisted SQLite setting `data_dir`
3. Platform default
4. **Refuse** live root inside git checkout (CARD-294 / `is_checkout_live_tree_path` → fall back to platform default)

Canonical layout under root (`DataDirPaths`):

| Path | Role |
|------|------|
| `database/autoreiv.db` | Operational SQLite (settings, custom_agents, agent_overrides, jobs, routines, sessions, …) |
| `wiki/` | Markdown vault (default; override via `AUTOREIV_WIKI_PATH` / explicit resolve) |
| `skills/` | Bundled/user skill trees (seed-if-missing from repo seeds) |
| `agents/` | Agent-adjacent FS artifacts |
| `templates/jobs/` | Job templates |
| `packs/<agent_id>/` | Live pack folders (`pack.json`, `skills/`, per-agent DBs) |
| `backups/` | Backup archives (or `AUTOREIV_BACKUP_DIR` / setting `backup_dir`) |

Per-agent DBs (`resolve_agent_storage_path` / `resolve_agent_memory_path`):

- `packs/<id>/<snake>_storage.db` — domain/application storage
- `packs/<id>/<snake>_memory.db` — cognitive memory (must not share storage path)

Boot / seed / reconcile (concrete call chain):

1. `create_app` → `bootstrap_data_dir(...)` (`src/web/app.py`)
2. `bootstrap_data_dir` → `ensure_layout` → optional migrate → `seed_bundled_skill_packs` → `seed_platform_pack_folders` → prune bled skills / orphan DBs (`resolver.py`)
3. `BuiltinAgentRegistry` boot path → `install_platform_agent_packs` (`src/infrastructure/agents/registry.py`, `src/infrastructure/skills/platform_packs.py`)
4. `DeclarativePackReconciler.reconcile` — purge **retired** platform ids from SQLite + disk; preserve custom (`src/infrastructure/skills/reconciler.py`)
5. Platform pack install: copy-if-missing from repo `platform-packs/` → `$DATA_DIR/packs/`; for **existing** platform agents, **sync** `system_prompt` / skill lists / tools from repo into SQLite **and** rewrite `pack.json`; `copytree(..., dirs_exist_ok=True)` for skills; **delete** dest skill dirs not present in repo source

Wiki:

- Default `root/wiki`; `WikiStore` falls back via `LEGACY_WIKI_STRINGS` + resolver (`src/domain/wiki/store.py`)
- Settings Studio surfaces `wiki_path` as read-only status text today (`settings.js`) — **no first-run folder picker / explicit reconnect UX**
- `ensure_layout` **mkdir** default wiki — silent create, not fail-closed on missing configured path

Import/export:

- `AgentPackService.export_folder` / `export_zip` / `import_path` (`src/application/agent_packs/service.py`) — filesystem interchange around `pack.json` + skills

Backup/restore:

- `DataDirBackupService` zips data tree; special-cases external wiki + SQLite snapshot (`src/infrastructure/data/backup.py`)

Schema anchors (`src/infrastructure/memory/schema.py`): `settings`, `agent_overrides`, `custom_agents`, jobs/routines/sessions, plus many operational tables — **profiles dual-written** with filesystem packs.

### Beat 3 — What will change (planning deliverables only)

This card delivers **analysis + decision**, not code:

1. Completed ownership **inventory matrix** (below) + deep audit brief under `docs/design/` — reviewed with Jacob
2. Options A–D compared against decision criteria (below)
3. Required mapping docs (seeder/reconciler paths, FKs/stable IDs, boot flow, wiki UX, failure modes) cited to concrete files
4. Product forks answered (section 6)
5. Migration phase plan agreed (section 7) — favoring additive schema + **dual-read validation**; dual-write only if explicitly bounded
6. Operator contracts listed for any future cutover (section 8)
7. ADR draft authored under `docs/adr/` only after walkthrough; set Accepted only with Jacob's OK
8. CARD-411 relationship decision: block / defer / narrow scope

### Beat 4 — What dies today (intent to retire; deletion deferred until build)

Fragile ownership patterns to **retire in the eventual build** (not deleted by this planning card):

- Treat AppData pack/skill trees as silently re-seedable mirrors of `platform-packs/`
- Boot-time **prompt/skill sync that overwrites** operator-visible files without `user_modified` / hash gates
- **Prune** of user skill folders solely because repo seed omitted them
- Dual canonical truth (SQLite profile **and** `pack.json`) without a single writer
- Silent wiki mkdir / legacy string fallbacks that hide a broken configured path
- One-shot mass delete of AppData content as a "migration"
- Folding this decision into CARD-411 implementation

---

## 1b. Recommended architecture (pending Jacob)

> **Audit complete (2026-09-21 ET).** Full brief:
> [`docs/design/CARD-413-ownership-audit-and-recommended-architecture.md`](../design/CARD-413-ownership-audit-and-recommended-architecture.md)
>
> **Recommendation**: Hybrid **C+** — SQLite canonical for mutable runtime registry (profiles, bindings, settings, jobs); filesystem canonical for wiki + pack **interchange**; repo canonical for platform defaults; reconcile via stable id + version/hash + `user_modified` (no silent overwrite/fallback); keep per-agent `storage.db` / `memory.db` + one operational `autoreiv.db`; manifest backup/restore; wiki first-run picker + fail-visible missing path.
>
> **Status**: Ready (planning). **`adr: none`** — ADR remains Proposed/none until Jacob walkthrough Accepts.
> **CARD-411**: defer / read-only until ADR Accepted.
> **Next**: Jacob reviews forks in the brief (≤6 defaults listed); reply **`continue`** to refine, or after ADR Accept proceed on a build successor — not this card alone.

---

## 2. Inventory matrix (artifact × ownership)

| Artifact | Current canonical owner | Writers | Readers | Upgrade / reseed behavior | Proposed options (A–D) |
|----------|-------------------------|---------|---------|---------------------------|------------------------|
| Platform packs (`platform-packs/*` → `packs/<id>`) | Repo seed; live copy under AppData | `seed_platform_pack_folders`, `install_platform_agent_packs` | Registry, Forge, runtime | Copy-if-missing; then sync prompt/skills/tools; may delete extra skill dirs | A harden sync; B DB blob; **C** DB registry + FS interchange; D CAS files + DB index |
| User/custom packs | AppData `packs/<id>` + `custom_agents` row | Forge/API, import | Registry, chat | Not re-seeded; reconciler preserves non-retired | A/C keep FS interchange; B DB-only |
| Skills / `SKILL.md` | FS under pack or `skills/` | Seed, install sync, editors | Kernel, Forge | Bundled seed-if-missing; platform skill sync can overwrite/prune | **Fork**: FS editable vs UI/export-only |
| Tool bindings | SQLite (`allowed_tools_json`, overrides) + pack.json fields | Install sync, Forge | Policy gate, runtime | Merged on platform sync (union + retired filter) | C: DB canonical; pack.json export projection |
| Agent profiles | SQLite `custom_agents` / `agent_overrides` + pack.json | Registry, install sync | Everywhere | Dual write; sync can rewrite prompts | C: DB canonical |
| Settings | SQLite `settings` | Settings API | Resolver, studios | Durable keys (`data_dir`, `backup_dir`, …) | Keep DB (all options) |
| Routines / jobs / sessions | SQLite operational tables | Orchestration | Observe, chat | Migrate with `autoreiv.db` | B/C storage.db |
| Cognitive memory | Per-agent `*_memory.db` | Memory repos | Chat, education | Already separate from storage | Keep separate (**hypothesis**) |
| Operational storage | `database/autoreiv.db` + per-agent `*_storage.db` | Many | Many | Backup zip snapshot | Clarify storage.db vs memory.db |
| Wiki Markdown / templates | FS `wiki_path` | WikiStore, tools | RAG, studios | Default mkdir; legacy path strings; external wiki in backup | C: FS canonical; picker + no silent fallback |
| Attachments / artifacts | Session/wiki FS + DB refs | Jobs, wiki | UI | Path-coupled | Manifest + stable IDs |
| Backups / exports | `backups/` zip + pack zip export | Backup service, pack service | Restore/import | Tree zip + external wiki | Manifest lists DB(s), wiki URI, hashes |

---

## 3. Options to compare (do not pre-decide)

| Option | Summary |
|--------|---------|
| **A. Filesystem-first + hardening** | Keep AppData packs/skills as live source; add hashes, `user_modified`, never prune user dirs, idempotent reconcile |
| **B. One SQLite for most state/content** | Profiles, skills bodies, bindings, settings, jobs in one DB; FS only for interchange snapshots |
| **C. Hybrid (hypothesis favorite)** | DB = mutable runtime registry; FS = wiki + export/import packs; repo = platform defaults; separate memory/storage DBs; versioned reconcile |
| **D. Content-addressed / versioned files + DB index** | Objects by hash on disk; DB indexes pointers/metadata; strong dedupe and rollback |

### Decision criteria

- Upgrade/reseed **idempotence** (second boot = no churn)
- User **editability** (files vs UI)
- Export/import **fidelity** (skills, bindings, stable IDs)
- Corruption/locking **blast radius**
- Migrations complexity
- Observability (what changed, why)
- Cross-platform paths
- Backup/restore **atomicity**
- Local-first ownership
- Performance
- Concurrency (multi-studio / multi-process)

---

## 4. Required analysis / mapping before ADR

Produce a short design brief (still docs) that cites:

| Area | Concrete paths to map |
|------|------------------------|
| Seeder / reconciler | `src/infrastructure/skills/platform_packs.py`, `reconciler.py`, `seed.py`, `bootstrap_data_dir` |
| AppData / user-data | `DataDirResolver.platform_default` / `resolve`, env keys `AUTOREIV_DATA_DIR` / `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` / `AUTOREIV_BACKUP_DIR` |
| Schema / tables | `src/infrastructure/memory/schema.py` (`custom_agents`, `agent_overrides`, `settings`, jobs/routines/sessions) |
| Stable IDs / FKs | agent id ↔ pack folder name ↔ tool name strings ↔ skill folder names |
| Boot flow | `src/web/app.py` `create_app`, `BuiltinAgentRegistry` boot path |
| Import/export | `src/application/agent_packs/service.py` |
| Backup/restore | `src/infrastructure/data/backup.py`, `migrate.py` |
| Wiki resolution | `resolver` wiki_path, `src/domain/wiki/store.py`, settings Studio surfacing |
| Failure modes | missing wiki path; partial seed; DB row without folder; folder without DB row; sync overwrite; restore without wiki |

---

## 5. Target hypothesis (not Accepted)

> **Hypothesis C+**: DB canonical for mutable runtime registry; files canonical for wiki + pack interchange; repo canonical for platform defaults; reconcile via stable id + version/hash + `user_modified`; **no silent overwrite/fallback**; separate **storage** vs **memory** DB roles; backup manifest enumerates DB(s), wiki path, content digest, pack export set.

Mark ADR `Proposed` only after Jacob walkthrough; Accept only on explicit approval.

---

## 6. Major product forks (questions for Jacob)

1. **Skills editing**: directly editable as files on disk, or only via UI with export-as-files?
2. **Built-in customization**: override-in-place vs fork-to-custom pack vs layered overlay?
3. **DB topology**: one operational DB vs separate `storage.db` / `memory.db` (platform-level) in addition to per-agent DBs?
4. **Wiki default path + first-run UX**: always picker? suggest under data root? OneDrive/Documents?
5. **Backup includes wiki?** always / opt-in / by-reference path only?
6. **Missing wiki path**: fail visibly (recommended) vs read-only mode vs explicit "reconnect" only — **no silent re-create elsewhere**?
7. **Export/import fidelity**: must round-trip skills + tool bindings + stable IDs?
8. **Migration rollback / downgrade**: support N-1 downgrade or forward-only with backup restore?

---

## 7. Migration phases (future build card; plan now)

1. Read-only inventory/audit (this card)
2. ADR Proposed → walkthrough → Accepted
3. Additive schema + **dual-read validation** (avoid unbounded dual-write)
4. Migration dry-run + report
5. Backup (manifest)
6. Migration execute
7. Verification operator contracts
8. Cutover (single writer)
9. Prune old seed paths
10. Rollback drill documented

**Note**: Dual-write is **not** automatically good — only if explicitly bounded with a kill switch and comparison metrics.

---

## 8. Operator contracts required before cutover

| ID | Contract |
|----|----------|
| OC-S1 | Built-in reconcile idempotent; user edits survive second boot |
| OC-S2 | Pack export → import fidelity (skills, tool bindings, stable IDs) |
| OC-S3 | Backup/restore restores DB(s), wiki path, content, manifest |
| OC-S4 | Upgrade migration preserves agents/skills/bindings; no invalid refs |
| OC-S5 | Configured wiki path persists; missing path fails visibly; path migrate + rollback verified |
| OC-S6 | Fresh install first-run folder picker; no duplicate fallback wiki |

---

## 9. Anti-theatre

| Concern | Proof bar |
|---------|-----------|
| Durable state | Contracts hit real AppData/temp user-data + SQLite, not mocks only |
| Studio/operator path | Settings/Forge/Wiki actions a human can see |
| Failure modes | Explicit tests for missing wiki, orphan pack folder, orphan DB row, reseed no-op |
| Proof | Named OC-S* gates in `tests/integration/operator_contracts/` (or successor) before Done |

---

## 10. Out of scope (this card)

- No product implementation
- No immediate mass migration
- No one-shot delete of AppData content
- No folding CARD-411 implementation into this decision
- No Accepted ADR without Jacob walkthrough
- No push / merge / tag

---

## 11. CARD-411 relationship

**CARD-411** (skill runbook YAML frontmatter, tool binding UI, Forge vs Factory separation) **depends on ownership**:

- If skills remain FS-canonical, Forge/Factory editors are file writers with reconcile rules
- If skills become DB-canonical, editors write DB and export projects files
- Tool binding UI must target the **single** canonical binding store

**Recommendation for discussion**: **Defer CARD-411 build** (or narrow to read-only inspector) until CARD-413 ADR is Accepted. Keep CARD-411 Ready but blocked on ADR outcome.

---

## 12. Acceptance criteria (planning / decision)

### Planning progress (executor)

- [x] Deep ownership audit + ownership map + C+ recommendation written to `docs/design/CARD-413-ownership-audit-and-recommended-architecture.md` (REQ-413-004 cite map).
- [ ] REQ-413-001..003 still need Jacob walkthrough / fork answers / option scoring sign-off.
- [x] CARD-411 defer/read-only recommendation recorded in brief + this card §1b / §11.


- [ ] **REQ-413-001 (Ubiquitous)**: THE DECISION PHASE SHALL review the ownership inventory matrix with Jacob; `continue` iterations remain planning only.
- [ ] **REQ-413-002 (Ubiquitous)**: THE DECISION PHASE SHALL score Options A–D against every stated criterion and name the selected option or hybrid.
- [ ] **REQ-413-003 (Event-driven)**: WHEN Jacob answers the product forks, THE CARD SHALL record those answers and their trade-offs.
- [ ] **REQ-413-004 (Ubiquitous)**: THE DESIGN BRIEF SHALL map and cite the concrete seeder, reconciler, schema, boot, import/export, backup/restore, and wiki paths above.
- [ ] **REQ-413-005 (State-driven)**: WHILE the ADR has not completed Jacob's walkthrough, THE ADR SHALL remain Proposed and this card SHALL keep `adr: none` until an ADR exists.
- [ ] **REQ-413-006 (Event-driven)**: WHEN the ADR is accepted, THE CARD SHALL link it and SHALL record the CARD-411 blocked/deferred/narrowed decision on both cards.
- [ ] **REQ-413-007 (Ubiquitous)**: THE BUILD SUCCESSOR SHALL reference operator contracts OC-S1..OC-S6 before cutover.
- [ ] **REQ-413-008 (Unwanted behavior)**: WHILE this planning card is active, THE REPOSITORY SHALL receive no product implementation, mass migration, or AppData deletion under CARD-413.

---

## 13. Human verification runbook (for this planning card)

1. Open `docs/cards/CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md`
2. Confirm status Ready, adr none, Four Beats present
3. Reply **`continue`** to refine forks/options, or after ADR acceptance reply **`build`** on the **implementation successor** (not this scaffold alone)

---

## 14. References (code)

- `src/infrastructure/data/resolver.py` — `DataDirResolver`, `DataDirPaths`, `bootstrap_data_dir`, `ensure_live_data_root`, `is_checkout_live_tree_path`, `resolve_agent_storage_path`, `resolve_agent_memory_path`, `prune_bled_platform_skills`, `prune_orphan_databases`
- `src/infrastructure/data/backup.py` — `DataDirBackupService`
- `src/infrastructure/data/migrate.py` — data-dir relocate helpers
- `src/infrastructure/skills/platform_packs.py` — `seed_platform_pack_folders`, `install_platform_agent_packs`, `cleanup_orphaned_platform_packs`
- `src/infrastructure/skills/reconciler.py` — `DeclarativePackReconciler`, `ReconciliationReport`
- `src/infrastructure/skills/seed.py` — `seed_bundled_skill_packs`
- `src/infrastructure/agents/registry.py` — `BuiltinAgentRegistry` (boot calls install/seed)
- `src/infrastructure/memory/schema.py` — SQLite DDL (`settings`, `custom_agents`, `agent_overrides`, jobs/routines/sessions, …)
- `src/application/agent_packs/service.py` — `AgentPackService` export/import
- `src/domain/wiki/store.py` — wiki root resolution / vault IO
- `src/web/app.py` — `create_app` → `bootstrap_data_dir`
- Repo seed tree: `platform-packs/`
- `.agents/rules/checkout-hygiene.md` — no live packs/DBs/wiki in checkout

---

## Policy decisions locked (2026-09-21)

Architecture: **Hybrid C+** per [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md) (**Proposed**).

| # | Fork | Locked decision |
|---|------|-----------------|
| 1 | Skills editing | Studios primary; readable files; direct edits set `user_modified` |
| 2 | Built-in customization | Layered overrides + explicit Fork to custom |
| 3 | DB topology | One `autoreiv.db` + per-agent storage/memory DBs |
| 4 | Wiki first-run | Deployment-mode aware: local = explicit path, no suggestion; Docker/daemon = compose env + volume required (no host picker) |
| 5 | Backup wiki content | Manifest always records wiki URI; file content **opt-in** |
| 6 | Missing wiki path | Fail visibly + reconnect/migrate only |

Also locked: export/import round-trips skills + bindings + stable IDs; forward-only migration with backup restore as rollback; CARD-411 deferred until ADR **Accepted**.

Exact next phrases: reply **continue** to refine the Proposed ADR; say clearly that you **Accept ADR-0056** when ready (then we mark Accepted and plan the implementation successor). Do **not** say **build** until Accept + successor card.

