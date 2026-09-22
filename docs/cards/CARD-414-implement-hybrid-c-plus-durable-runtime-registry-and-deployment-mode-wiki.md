---
id: CARD-414
title: "Implement Hybrid C+ Durable Runtime Registry, Versioned Reconciliation, Manifest Backup, and Deployment-Mode Wiki"
status: In Review
created: 2026-09-21
adr: docs/adr/0056-durable-runtime-registry-hybrid-c-plus.md
labels:
  - type:feat
  - type:architecture
  - area:storage
  - area:packs
  - area:wiki
  - area:deploy
---

# [CARD-414] Implement Hybrid C+ Durable Runtime Registry, Versioned Reconciliation, Manifest Backup, and Deployment-Mode Wiki

> **Status**: In Review  
> **Created**: 2026-09-21  
> **ADR Reference**: [ADR-0056](../adr/0056-durable-runtime-registry-hybrid-c-plus.md) (**Accepted**)  
> **Parent planning**: [CARD-413](./CARD-413-durable-runtime-registry-platform-reconciliation-portable-pack-interchange-and-configurable-wiki-root.md) (Done)  
> **Design brief**: [ownership audit](../design/CARD-413-ownership-audit-and-recommended-architecture.md)  
> **Labels**: `type:feat`, `type:architecture`, `area:storage`, `area:packs`, `area:wiki`, `area:deploy`

---

## Gate language

| Jacob reply | Meaning |
|-------------|---------|
| **continue** | Refine phasing / acceptance before code |
| **build** | Start implementation on a feat branch from `qa` |
| **merge to qa** | After In Review + live test |

---

## 1. Four Beats

### Beat 1 — What Jacob means

Execute **Accepted ADR-0056 (Hybrid C+)**: SQLite-canonical control plane; filesystem wiki + pack interchange; versioned platform reconciliation with `user_modified`; Windows/Linux local explicit wiki path (no suggestion); Docker/daemon wiki via env + volume with **hard-fail start** if missing; manifest backup; operator contracts OC-S1..S6.

### Beat 2 — What AutoReiv does now

See CARD-413 audit: dual-write pack sync, destructive skill prune, silent wiki mkdir/fallback, zip backup without manifest, Docker not hard-failing on missing wiki.

### Beat 3 — What will change

Phased implementation (prefer additive schema + dual-read validation; avoid unbounded dual-write):

1. Schema: seed provenance + `user_modified` + durable `wiki_path` setting
2. Stop destructive platform skill prune / silent prompt overwrite; hash-gated apply
3. SQLite single writer for profiles/bindings; `pack.json` export projection
4. Wiki: local first-run explicit path gate; Docker hard-fail start; Settings status/reconnect/migrate
5. Manifest backup + restore dry-run / restore
6. Migration dry-run → backup → execute → OC-S1..S6 → cutover → prune seed-as-live assumptions
7. Compose docs: required `AUTOREIV_WIKI_PATH` + volume examples for Windows/Linux hosts

### Beat 4 — What dies today

- Silent AppData re-seed mirrors of `platform-packs/`
- Boot overwrite of operator-touched prompts/skills/tools
- Skill dir prune because repo omitted them
- Silent wiki fallback mkdir
- Docker boot without configured wiki path/volume
- Treating `pack.json` as boot source of truth

---

## 2. Operator contracts (must pass before Done)

| ID | Contract |
|----|----------|
| OC-S1 | Built-in reconcile idempotent; user edits survive second boot |
| OC-S2 | Pack export → import fidelity (skills, bindings, stable IDs) |
| OC-S3 | Backup/restore restores DB(s), wiki URI/policy, optional content, manifest |
| OC-S4 | Upgrade migration preserves agents/skills/bindings; no invalid refs |
| OC-S5 | Configured wiki path persists; missing path fail-visible locally; migrate + rollback verified |
| OC-S6 | Local first-run explicit wiki config; Docker hard-fail if wiki missing; no duplicate fallback wiki |

---

## 3. Acceptance criteria (EARS)

- **[REQ-414-001]**: THE SYSTEM SHALL treat operational SQLite as the sole writer for agent profiles and tool/skill bindings after cutover.
- **[REQ-414-002]**: WHEN `user_modified` is true, THE SYSTEM SHALL NOT overwrite or prune that artifact on boot/upgrade.
- **[REQ-414-003]**: WHEN Docker/daemon wiki path/volume is missing, THE SYSTEM SHALL hard-fail start.
- **[REQ-414-004]**: WHEN local wiki path is unset, THE SYSTEM SHALL block wiki use until an explicit path is configured (no suggested path; no silent vault).
- **[REQ-414-005]**: THE SYSTEM SHALL emit backup manifests listing DB roles, wiki URI, digests, and pack set.
- **[REQ-414-006]**: THE SYSTEM SHALL pass OC-S1..S6 under temp user-data before In Review.

---

## 4. Out of scope

- Full CARD-411 Forge/Factory editor redesign (deferred until this cutover)
- CAS / Option D storage
- Splitting platform operational DB into multiple files in v1
- Mass delete of AppData as "migration"

---

## 5. Human verification (after build)

1. Local: fresh data dir → must configure wiki path → vault scaffolds only after confirm.
2. Edit a platform skill / remove a tool → restart twice → changes survive; no silent re-add/prune.
3. Export pack → import → skills/bindings/ids match.
4. Backup with manifest → restore → DBs + wiki URI policy correct.
5. Docker compose without wiki env/volume → container/process **fails start** with clear error.
6. Docker compose with wiki volume + env → starts; wiki usable.


## 6. Live-test steps (Jacob)

1. **Checkout** `feat/card-414-hybrid-c-plus-runtime-registry` on Jarvis (`D:\Projects\Active\AutoReiv`). If only box apply artifacts exist, apply patch/bundle from `/workspace/card414-apply/` first (do not push).
2. **Fresh local data dir**: unset wiki → Settings shows unset / fail-visible; set an explicit path + confirm scaffold → `00_Inbox/` appears only after confirm. No suggested default path.
3. **Operator edit survive**: remove a tool from a platform agent in Settings/Forge; add a custom skill folder under `packs/<id>/skills/`; restart twice → tool stays removed; custom skill dir not pruned; `user_modified` stays true.
4. **Export/import**: export agent pack zip → import → stable id + tools/skills match.
5. **Backup**: create backup zip → confirm `backup-manifest.json` lists operational DB, wiki URI, packs; restore dry-run / restore on a temp data dir.
6. **Docker**: `AUTOREIV_DEPLOY_MODE=docker` without `AUTOREIV_WIKI_PATH` → process **fails start**. With wiki volume + env → starts and wiki usable.
7. **OC suite**: `uv run python -m pytest tests/integration/operator_contracts/ -q` → OC-1..3 and OC-S1..S6 green.

