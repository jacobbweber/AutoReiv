# [ADR-0056] Durable Runtime Registry (Hybrid C+): SQLite Canonical Control Plane, Filesystem Wiki & Pack Interchange, Versioned Platform Reconciliation

> **Status**: Accepted  
> **Date**: 2026-09-21  
> **Accepted**: 2026-09-21 (Jacob: Accept ADR-0056 with Docker hard-fail rule)  
> **Deciders**: Jacob (Visionary & Product Owner), AutoReiv Harness Engineer  
> **Consulted**: CARD-413 ownership audit  
> **Related Cards**: [CARD-413](../cards/CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md), [CARD-411](../cards/CARD-411-skill-runbook-yaml-frontmatter-tool-binding-ui-and-forge-vs-factory-separation.md) (Option A build unblocked 2026-09-22), [CARD-412](../cards/CARD-412-test-suite-hygiene-obsolete-test-pruning-and-consolidation-audit.md) / [ADR-0055](./0055-operator-contract-testing-and-suite-hygiene.md)  
> **Design brief**: [CARD-413 ownership audit & recommended architecture](../design/CARD-413-ownership-audit-and-recommended-architecture.md)  
> **Supersedes / Softens**: Boot-time treatment of AppData `packs/` trees as silently re-seedable mirrors of repo `platform-packs/`; silent wiki mkdir / legacy path fallback as configuration substitutes

> **Amendment (2026-09-21, live-test UX)**: Local mode defaults the wiki folder to `{data_root}/wiki` on first boot when unset (persist `wiki_path`, scaffold that one folder). Do **not** create a second vault name (e.g. `wiki-vault`). Docker/daemon hard-fail when unset/missing/unreadable is **unchanged**. Settings UI uses plain “Wiki folder” language (no ADR/card friction copy).


---

## 1. Context & Problem Statement

AutoReiv today dual-owns agent packs and skills:

- Studios and runtime profiles already treat **SQLite** (`database/autoreiv.db`) as the agent brain (profiles, overrides, tool bindings, settings, jobs/sessions).
- Boot (`bootstrap_data_dir` → `install_platform_agent_packs` → `DeclarativePackReconciler`) still treats **AppData pack folders** as live mirrors of repo `platform-packs/`: syncs prompts/tools into SQLite, rewrites `pack.json`, `copytree`s skills, and **deletes** destination skill dirs not present in the repo.

That dual truth causes upgrade fragility: operator edits overwritten, custom skills under platform pack ids pruned, tool removals re-added by union-merge, orphan folders/DB rows, and invalid skill/tool references.

Wiki path resolution compounds the problem: `ensure_layout` silently `mkdir`s the default vault; legacy path strings fall back; Settings shows `wiki_path` as read-only status with **no** first-run picker or fail-visible reconnect. A missing configured vault can appear as an empty “working” wiki.

Jacob’s product intent (local-first, operator-owned, Studio-driven, wiki as human documents, upgrades must not trash user work) requires a single coherent ownership model before large editor work such as CARD-411.

---

## 2. Decision Drivers

* Upgrade/reseed **idempotence** (second boot = no destructive churn).
* Operator **editability** without silent clobber.
* Export/import **fidelity** (skills, bindings, stable IDs).
* Corruption / locking **blast radius**.
* Local-first ownership; user data never in the git checkout.
* Human-friendly wiki Markdown vaults.
* Backup/restore **provenance** (manifest), not blind zip-only.
* Migration cost bounded enough to execute with operator contracts OC-S1..S6.
* **Windows + Linux** deploy targets, including local serve, OS daemon, and **Docker Compose** with env/volume configuration.

---

## 3. Considered Options

| Option | Summary | Outcome |
|--------|---------|---------|
| **A. Filesystem-first + hardening** | Keep AppData packs as live source; add hashes / never-prune | **Rejected** — leaves dual canonical truth; fights SQLite-backed Studios |
| **B. One SQLite for most state/content** | Profiles, skill bodies, wiki bodies in one DB | **Rejected** — hurts human wiki/skill workflows; larger blast radius |
| **C+ Hybrid (Chosen)** | SQLite = mutable runtime registry; FS = wiki + interchange/skill store; repo = platform defaults; versioned reconcile; separate per-agent storage/memory DBs; manifest backup | **Accepted direction (Proposed)** |
| **D. Content-addressed files + DB index** | Hash objects on disk; DB pointers | **Deferred** — valid later evolution under C+ rules; too costly as first cutover |

---

## 4. Decision Outcome (Proposed)

### 4.1 Canonical ownership

| Concern | Canonical owner |
|---------|-----------------|
| Agent profiles, overrides, tool/skill bindings, settings, jobs/routines/sessions, approvals, telemetry meta | **Operational SQLite** `database/autoreiv.db` |
| Cognitive memory | **Per-agent** `packs/<id>/<snake>_memory.db` |
| Agent domain / application storage | **Per-agent** `packs/<id>/<snake>_storage.db` |
| Wiki note bodies and templates | **Filesystem vault** at an **explicit** configured path |
| Platform defaults (stock prompts, stock skills, stock tools) | **Repo** `platform-packs/` + skill seeds |
| Portable packs | **Export/import artifacts only** (materialized folder/zip when the operator asks) |

Live AppData pack trees may remain a **skill body store** and export home, but must **not** be treated as silently re-seedable mirrors of the repo.

`pack.json` becomes an **export projection** of the SQLite registry, not a second source of truth for boot sync.

### 4.2 Reconciliation rules

For each platform artifact keyed by **stable id** (`agent_id`, skill id, tool name):

1. Record seed provenance: `seed_id`, `seed_version` and/or `content_hash` of last applied repo revision.
2. Set **`user_modified=true`** when the operator (or Studio) changes profile/skills/bindings away from the last applied seed hash — including advanced direct file edits to skill bodies.
3. On boot / upgrade:
   - If not `user_modified` and seed hash differs → apply seed update (idempotent).
   - If `user_modified` → **never** overwrite; optionally surface “upstream update available.”
   - **Never** delete skill dirs solely because the repo omitted them when `user_modified` or when the skill is not on the retired list.
4. Retired platform ids keep an explicit purge list; custom agents must not silently reuse retired id strings.
5. Tool bindings: **SQLite is the sole writer**. Removals stick. Seed may propose adds only when not `user_modified`, or via explicit “accept upstream.”
   - **Exception [CARD-425]**: one named additive grant may append `native-tool-engineering` plus `register_native_tool` / `plan_native_folder` onto a `user_modified` developer allowlist. The grant does not rewrite the prompt, other allowlist entries, or MCP servers. The skill id is recorded in the `platform_user_modified_skill_grants` setting. After that record exists, a later removal stays removed.
   - **Exception [CARD-426]**: when a `user_modified` developer already has `packs/developer/skills/native-tool-engineering/SKILL.md` and that body is missing the legacy-loader warning marker `<!-- autoreiv:native-tool-legacy-loader -->` and the heading `## Not the legacy pack loader`, boot appends only the seed warning section. The rest of that file, the developer prompt, and other skill bodies stay. If the marker or that heading is already present, the file is left alone. Tools Studio catalog labels do not read this file.
   - **Exception [CARD-433]**: when a `user_modified` developer system prompt does not mention `scaffold_agent_pack`, boot appends one authoring paragraph and leaves the existing text in place. The append is recorded in `platform_user_modified_prompt_appends`. After that record exists, a later deletion stays deleted. This does not rewrite a non-`user_modified` seed prompt or add `save_agent_specification` to the allowlist.

### 4.3 Locked product-policy forks (Jacob 2026-09-21)

| # | Fork | Decision |
|---|------|----------|
| 1 | Skills editing | **Studios primary**; files remain readable under the skill store; direct file edits set `user_modified` |
| 2 | Built-in customization | **Layered overrides** + explicit **Fork to custom pack** for large divergence; no silent in-place clobber of seed |
| 3 | DB topology | **One** operational `autoreiv.db` + per-agent `*_storage.db` / `*_memory.db` (no platform DB split in v1) |
| 4 | Wiki first-run | **Deployment-mode aware** (see section 4.4): local Windows/Linux **default to `{data_root}/wiki`** when unset (persist + scaffold that one folder); Docker/daemon require wiki via **compose/env + volume** and **hard-fail start** if missing (no host folder picker inside the container) |
| 5 | Backup vs wiki content | Manifest **always** records configured wiki URI; **including wiki file content is opt-in** |
| 6 | Missing wiki path | **Fail visibly** + reconnect/migrate only — **never** silent recreate elsewhere |

Also locked: export → import **round-trips** skills + tool bindings + stable IDs; migrations are **forward-only** with restore-from-pre-cutover backup as rollback.

### 4.4 Wiki UX invariants (deployment-mode aware)

AutoReiv targets **Windows and Linux**, including local serve, OS daemon, and **Docker Compose** deployments. Wiki configuration MUST be explicit in every mode. Silent `mkdir` of a fallback vault is forbidden.

#### Local Windows / Linux (machine-local control plane)

1. First run / empty wiki config: **default** to `{data_root}/wiki` (e.g. `%LOCALAPPDATA%\AutoReiv\wiki`). Adopt on boot: persist `wiki_path`, create/scaffold **that one folder**.
2. Do **not** create or suggest a second vault name (e.g. `wiki-vault`).
3. Settings shows plain “Wiki folder” with the path filled; operator may change it. Optional “Create standard folder layout if missing” defaults checked on adopt/save.
4. Persist chosen path as durable setting (distinct from env override). Env may still override for advanced operators.
5. If configured path missing/unreadable: **fail visibly** + reconnect/migrate — never create a different fallback vault.

#### Docker Compose / headless daemon

1. Wiki content is a **volume** (or a subdirectory of the data volume). Compose MUST document required env and mounts.
2. Required deploy configuration (at least one):
   - `AUTOREIV_WIKI_PATH` pointing at the in-container mount path, or
   - wiki living under `AUTOREIV_DATA_DIR` with an explicit durable `wiki_path` / documented convention that is set at deploy time (not invented at runtime).
3. A browser **cannot** mount a host directory into the container. There is **no** OS folder picker inside Docker. First-run prompt in Docker means Settings/onboarding UI that tells the operator to set compose env + volume, or a degraded/unready state until configured.
4. If wiki path/volume is missing at runtime: **fail visibly** (wiki subsystem fail-closed; onboarding/Settings banner; health/ready signal may report degraded). Do **not** silently create `/data/wiki` (or similar) as a substitute for deploy configuration.
5. **Hard-fail start if wiki missing** (Jacob lock): process/container start MUST fail closed when AUTOREIV_WIKI_PATH (or the documented deploy-time wiki path) is unset, unreadable, or the volume mount is absent. Compose MUST document required env + volume. No boot-for-diagnostics exception in Docker/daemon mode.

#### Shared invariants

- Settings Studio shows editable path / status (exists, missing, external, docker-mounted) - not read-only display only.
- Backup manifest always records configured wiki URI; including wiki file bytes remains **opt-in**.
- Cross-platform path handling must honor Windows and POSIX roots via existing `DataDirResolver` rules; checkout live-tree refuse remains in force.


### 4.5 Interchange

- **Export** materializes `pack.json` + skills from SQLite + skill store.
- **Import** writes SQLite registry + stores skill bodies under controlled pack home.
- Runtime boot must not re-copy from `platform-packs/` except first install of missing ids and hash-gated non-`user_modified` updates.

### 4.6 Manifest backup / restore

Backups include a manifest enumerating operational DB, per-agent storage/memory DBs (paths + digests), configured wiki URI, optional inlined wiki content + digest, pack export set, app/schema provenance. Restore validates the manifest and never invents a second wiki silently.

### 4.7 CARD-411

**Build unblocked (2026-09-22).** This ADR is Accepted and the CARD-414 cutover is on `qa`. Jacob locked Option A: Forge is agent identity and RBAC plus a read-only runbook inspector; Factory is the sole writer of skill bodies and tool bindings. Bindings persist in operational SQLite (`skill_tool_bindings` / `skill_binding_meta`). AppData `pack.json` is not a second live source of truth for those bindings.

### 4.8 Operator contracts before cutover

OC-S1..S6 as defined on CARD-413 / the design brief (idempotent reconcile + user edits survive; export/import fidelity; manifest backup/restore; migration preserves refs; wiki path persist + fail-visible missing; first-run explicit wiki config (local path gate / Docker env+volume) with no duplicate fallback wiki). Proof home: `tests/integration/operator_contracts/` per ADR-0055.

---

## 5. Consequences

### Positive

* Single writer for control-plane state; upgrades become predictable.
* Operator edits and tool removals stick.
* Wiki remains human Markdown with honest path UX.
* Export/import and backup become real product contracts, not side effects of seeding.

### Negative / risks

* Migration work touches boot, Forge, Settings, backup, and pack services — must be phased.
* Operators who relied on editing platform pack files in AppData as the “live source” must learn Studio-primary + `user_modified` semantics.
* Local first-run now defaults to `{data_root}/wiki` (amendment 2026-09-21) to reduce friction while keeping a single explicit owned path.
* Docker Compose requires intentional wiki volume/env at deploy time; operators cannot use a host folder picker inside the container.
* Docker/daemon **hard-fails start** when wiki path/volume is missing (accepted by Jacob).

### Migration posture (implementation successor; not this ADR alone)

1. Accept this ADR.
2. Additive schema (`user_modified`, seed hash/version, durable `wiki_path`) + dual-**read** drift reports (avoid unbounded dual-write).
3. Disable destructive platform skill prune / silent prompt overwrite behind hash gates.
4. Wiki picker + fail-visible path UX.
5. Manifest backup (additive) + restore dry-run.
6. Migration dry-run → backup → execute → OC-S1..S6 → cutover → prune obsolete seed-as-live assumptions → rollback drill = restore pre-cutover archive.

---

## 6. Compliance

* Status is **Accepted** (2026-09-21).
* No product implementation under CARD-413 scaffolding alone; implementation requires successor **build** card(s) (CARD-414+).
* Agents must not reintroduce silent AppData re-seed mirrors or silent wiki fallbacks after Accept.
