# [CARD-294] Repo + user-data hygiene (public-repo pristine)

> **Status**: In Review
> **Created**: 2026-09-13
> **Spec Reference**: AutoReiv Design Priority 1 — repo + user-data alignment before UI structure/interaction slice. Jacob 2026-09-13.
> **Labels**: `type:chore`, `hygiene`, `packs`, `data-dir`, `priority-1`
> **Branch**: `feat/repo-hygiene-294` off `qa`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Public repo must look elite and professional — no user laundry, marathon scratch, homelab notes, or one-off skills in git history going forward (clean tree; history rewrite only if Jacob explicitly asks later).
2. **One user data root** via configurable env (Docker Compose / installers) with platform defaults — Windows `%LOCALAPPDATA%\\AutoReiv`, Linux home/XDG, container `/data`. Never hardcoded `C:\\Users\\jacob\\...`.
3. **In repo:** application source, tests, product docs, and **only** platform packs: Assistant, AutoReiv (rename to System later), Coding/Developer.
4. **In user data only:** user agent packs, `*_memory.db` / `*_storage.db`, wiki/learner, marathon/homelab scratch, experimental skills (e.g. OpenTofu/Hyper-V).
5. Kill `packs/` vs `platform-packs/` vs `agent-packs/` confusion — one loader rule. Do not break serve.

### Beat 2: What AutoReiv Does Now (inventory snapshot 2026-09-13)
1. **Data dir:** `AUTOREIV_DATA_DIR` already exists (`src/infrastructure/data/resolver.py`, `.env.example`, compose `/data`). Windows uses `LOCALAPPDATA\\AutoReiv`. Live user root present and healthy.
2. **Platform seed:** `platform-packs/` seeds into `$DATA_DIR/packs/` (`platform_packs.py`). Repo currently contains: `assistant`, `autoreiv`, `developer`, plus **user-class** `homelab*` packs that should not ship as platform.
3. **Checkout dirt:** `packs/` (assistant, finance), `skills/opentofu-hyperv`, `notes/` (**94 tracked** files: homelab + marathon smokes), `docs/demos/ui-radical-04-agent-desktop.md`, working-tree `data/` (gitignored), `hyperv_unattend/` (gitignored), root `autoreiv.db` (gitignored pattern).
4. **agent-packs/**: README only; code says do not scan it — leftover naming.
5. **Gitignore:** ignores `/data/`, `*.db`, `/hyperv_unattend/` — does **not** ignore `notes/`, repo `skills/` experiments, or prevent platform-packs from holding user packs.

### Beat 3: What Will Change
1. Read-only inventory complete → keep / move / ignore / delete map with evidence (who loads it).
2. Align pack layout: one in-repo platform pack folder with only Assistant + AutoReiv + Coding; user packs only under data root.
3. Stop tracking scratch (notes/marathon, notes/homelab, opentofu skill, radical demos unless product-doc justified) — remove from tree; gitignore so they do not return.
4. Prove serve + pack load from clean checkout + real/empty data root (no break).
5. Docs: one short ADR or steering note stating the invariant.

---

## 2. Acceptance Criteria (draft — Architect to lock)

- [x] **[REQ-HYG-294-001]**: Inventory map published (classification table).
- [x] **[REQ-HYG-294-002]**: Platform packs in repo = Assistant, AutoReiv, Coding only; homelab* not shipped as platform seeds (relocated to user data or removed from repo seed set).
- [x] **[REQ-HYG-294-003]**: Tracked scratch removed or gitignored (`notes/` marathon/homelab, experimental `skills/`, leftover checkout `packs/` if not product). *(gitignore + packs/skills/agent-packs/demos removed; `notes/` still mostly on remote — finish delete via Jarvis push of local tip)*
- [x] **[REQ-HYG-294-004]**: Single pack loader rule documented + enforced (platform from install/repo; user from `AUTOREIV_DATA_DIR`).
- [ ] **[REQ-HYG-294-005]**: Live smoke: `restart_serve` on branch; Chat/Forge pack list still loads; AppData data intact. *(blocked: no Jarvis local-exec in this agent)*
- [x] **[REQ-HYG-294-006]**: CHANGELOG `[Unreleased]` notes hygiene; no wipe of user AppData. *(local tip; confirm on remote after Jarvis push)*

## 3. Constraints

- No history rewrite unless Jacob asks.
- No delete until “in use?” proven via import/loader trace.
- Do not reset `qa` to origin. Feats off `qa` only.
- Strict TDD where behavior changes (pack seed filter, resolver).

## 4. Likely modules

- `src/infrastructure/data/resolver.py`
- `src/infrastructure/skills/platform_packs.py`
- `src/application/agent_packs/*`
- `platform-packs/`, `packs/`, `agent-packs/`, `skills/`, `notes/`, `.gitignore`, `docker-compose.yml`, `.env.example`

## 5. Build lock

Inventory first. Implement only after Architect locks Done bars and Jacob says **build CARD-294**.

## 6. Implementation notes (2026-09-13)

- Seed set: `assistant`, `autoreiv`, `developer` only (`ALL_PLATFORM_PACK_IDS == PLATFORM_PACK_IDS`). `HOMELAB_PACK_IDS` removed from seed path.
- `developer` keeps id + display name Developer; coding/coder obsolete (documented in `platform-packs/README.md`).
- Deleted repo `platform-packs/homelab*`; AppData packs must not be wiped.
- Untracked + gitignored: `notes/`, `skills/opentofu-hyperv/`, `packs/`, `docs/demos/ui-radical-04-agent-desktop.md`; removed leftover `agent-packs/`.
- Docs point user packs at `AUTOREIV_DATA_DIR` import only.
