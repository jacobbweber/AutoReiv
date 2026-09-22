# CARD Investigation: Wiki 01_Notes Pollution on Scaffold/Establish

**Status:** Investigation only — no fixes applied, no push/merge  
**Branch tip investigated:** `feat/card-414-hybrid-c-plus-runtime-registry` @ `0344a360`  
**Compared to:** `qa` @ `ea113e9a` (`src/domain/wiki/store.py` scaffold list already cleaned on both)  
**Machine note:** Jarvis Shell unavailable this session; code trace from box mirror. Confirm empty-dir leftovers on Jacob’s live vault under `%data%/wiki/01_Notes` when implementing.  
**Date:** 2026-09-21 ~23:22 ET

---

## Symptom

On establish/scaffold, unwanted **directories** appear under `01_Notes/`:

| Relative path under `01_Notes/` |
|---------------------------------|
| `computer_science/artificial_intelligence` |
| `general/notes` |
| `operations/diagnostics` |
| `operations/worklog` |
| `systems_engineering/observability` |

**Desired:** `01_Notes/` empty on establish (directory exists, zero children). Templates/tag-authority live under `02_Resources/_Templates/` only.

---

## Root cause timeline

### Historical creator (exact match) — PRE CARD-406

Commit **before** `69c8ceb7` (`fix(chat,wiki): restore chat input render and vanilla wiki seeding [CARD-406]`) had `WikiStore.scaffold()` mkdir the **exact** polluted set:

```text
01_Notes/computer_science/artificial_intelligence
01_Notes/systems_engineering/observability
01_Notes/operations/worklog
01_Notes/operations/diagnostics
01_Notes/general/notes
```

plus top-level numbered folders. `_seed_starter_notes_if_empty()` also wrote starter `.md` files into those paths (e.g. `local_agent_architecture.md`, `telemetry_and_metrics.md`).

### Current tip (post CARD-406)

`scaffold()` directories list is **only**:

- `00_Inbox`
- `01_Notes`  ← bare folder
- `02_Resources/operating_manuals`
- `02_Resources/_Templates`
- `03_Archive`

`_seed_starter_notes_if_empty()` is a **no-op** (`store.py:629-634`) — intentionally vanilla.

**Fresh empty vault + current tip scaffold does NOT recreate the five taxonomy dirs.**

### Why Jacob still sees them “on scaffold”

Ranked:

1. **P0 leftover vaults (most likely):** Older scaffolds already created empty (or formerly seeded) domain/topic dirs. Current `scaffold()` is additive `mkdir(..., exist_ok=True)` and **never deletes** empty children under `01_Notes/`. Re-running Settings “Create standard folder layout” / boot scaffold / `WikiService`/`wiki_tools` `.scaffold()` leaves pollution in place.
2. **P1 test gap:** `tests/unit/wiki/test_vanilla_wiki_seeding.py` asserts no `*.md` under `01_Notes`, but **does not** assert `01_Notes` has no subdirectories — regression of silent mkdir lists wouldn’t be caught if only empty dirs returned.
3. **P2 ongoing mkdir parents (not the five-pack, but can recreate similar trees):**
   - `create_note` → `target_path.parent.mkdir(parents=True)` (`store.py:916`) when writing non-inbox notes to `01_Notes/<domain>/<topic>/`.
   - `migrate_legacy_vault` moves `notes/**` preserving relative paths into `01_Notes/` (`store.py:670-677`) — can resurrect `operations/worklog` etc. from legacy trees.
   - `cleanup_vault` may `mkdir` `01_Notes/weekly` when relocating legacy weekly notes (`store.py:1555-1559`) — different path than `operations/worklog`, still a non-empty taxonomy under Notes.
4. **Docs drift:** Archived specs / CARD-406 notes still mention seeding into `notes/computer_science/...` and `operations/worklog` (`docs/archive_artifacts/...`, `docs/cards/CARD-406-...`). Not executable, but confuses operators.

`tag-authority.md` still **documents** domains `computer_science`, `operations`, `systems_engineering` as tag taxonomy text (`store.py:546-570`) — that is content under `_Templates`, **not** folder creation. Keep text; do not mkdir from it.

---

## Call sites that invoke scaffold/establish

| Site | Behavior |
|------|----------|
| `WikiStore.scaffold` | `src/domain/wiki/store.py:510` |
| `WikiService.__init__` | `src/application/wiki/service.py:20-21` → scaffold |
| `WikiTools` | `src/application/skills/wiki_tools.py:22-23` |
| Boot local default | `src/web/app.py:150-153` `scaffold(seed_starter=False, auto_migrate=False)` |
| Settings save path | `src/web/routers/settings.py:123` when `confirm_scaffold` |
| `DataDirResolver.ensure_layout(..., scaffold_wiki=True)` | mkdir wiki root only (`resolver.py:260-267`) |
| `get_tree` / many store ops | call `scaffold()` first (`store.py:1891` etc.) |

None of the tip call sites re-add the five-pack mkdirs; they **preserve** existing pollution.

---

## Full scrub candidate list

### A. Empty taxonomy dirs to remove (safe if empty)

Delete if present and empty (bottom-up):

1. `01_Notes/computer_science/artificial_intelligence`
2. `01_Notes/computer_science` (if empty after)
3. `01_Notes/systems_engineering/observability`
4. `01_Notes/systems_engineering` (if empty after)
5. `01_Notes/operations/diagnostics`
6. `01_Notes/operations/worklog`
7. `01_Notes/operations` (if empty after)
8. `01_Notes/general/notes`
9. `01_Notes/general` (if empty after)

### B. Related leftovers to consider (policy)

| Path | Notes |
|------|-------|
| `01_Notes/weekly/` | Created by `cleanup_vault` relocation — not in Jacob’s list; decide keep-as-warehouse-topic vs scrub-if-empty |
| Legacy `notes/**` | Migrate then remove; migrating copies pollution structure into `01_Notes` |
| Starter `.md` if any remain | `welcome_to_autoreiv.md`, `local_agent_architecture.md`, `telemetry_and_metrics.md` — delete from `00_Inbox` / `01_Notes` if found (CARD-406 intent) |

### C. Code / test scrub (prevent reintroduce)

| Item | Action |
|------|--------|
| `WikiStore.scaffold` directories list | Guard/comment: never re-add domain/topic under `01_Notes` |
| New `scrub_empty_seed_taxonomy()` or fold into `scaffold`/`cleanup_vault` | Remove A-list empty dirs on establish |
| `test_vanilla_wiki_seeding.py` | Assert `list((wiki_root/'01_Notes').iterdir()) == []` |
| Optional migration test | Pre-seed the five dirs empty → scaffold/scrub → gone |
| Docs | Strike executable expectations in non-archive cards that still say seed those folders |

### D. Do **not** scrub

- `02_Resources/_Templates/**` (tag-authority, note templates, structured templates)
- `02_Resources/operating_manuals/**` if operator content exists
- Non-empty `01_Notes/<domain>/<topic>/*.md` real warehouse notes (only remove **empty** seed dirs unless Jacob confirms wipe)

---

## Ready card draft body

### Title
Wiki establish: scrub polluted 01_Notes taxonomy dirs; keep Notes empty

### Four Beats

**1. Context**  
Pre-CARD-406 `WikiStore.scaffold()` mkdir’d domain/topic folders under `01_Notes` (computer_science/AI, systems_engineering/observability, operations/worklog+diagnostics, general/notes) and seeded demo notes. CARD-406 stopped creating them on fresh vaults, but existing vaults keep empty dirs forever because scaffold never deletes children. Vanilla tests only assert no `.md` files, so empty pollution dirs go unnoticed. Jacob wants `01_Notes` empty on establish.

**2. Goal**  
On establish/scaffold (and a one-shot cleanup for existing vaults), `01_Notes/` has zero child directories or files. Canonical templates remain under `02_Resources/_Templates/`. Real graduated notes elsewhere are not destroyed.

**3. Approach**  
- Add an idempotent scrub of the known empty seed taxonomy paths (and empty parents) invoked from `scaffold` and/or `cleanup_vault` / Settings confirm_scaffold.  
- Strengthen `test_vanilla_wiki_seeding` to forbid any children under `01_Notes`.  
- Add a regression test that plants the five empty dirs then asserts scrub removes them.  
- Do not reintroduce domain mkdir lists; leave tag-authority text as documentation only.

**4. Done when**  
Fresh tmp wiki after scaffold: `01_Notes` empty. Vault with only the five empty dirs: after scrub/scaffold, gone. Vault with a real note under another domain: note kept. Settings “Create standard folder layout” does not recreate the five-pack. Tests green; CHANGELOG note.

### Acceptance
- [ ] Fresh `WikiStore(tmp).scaffold(seed_starter=True)` → `01_Notes` has no children.
- [ ] Planting the five empty paths then running scrub/scaffold removes them.
- [ ] Non-empty note paths under `01_Notes` are not deleted by scrub.
- [ ] `test_vanilla_wiki_seeding` asserts no subdirs (not only no md).
- [ ] Boot/Settings establish paths documented; no starter md reintroduced.
- [ ] CHANGELOG Unreleased; card linked.

### Out of scope
- Chat Studio durability / Save to Wiki (separate card).
- Redesigning domain/topic taxonomy for curated notes.
- Deleting operator-authored notes.
- Forcing migrate of legacy `notes/` content beyond existing migrate_legacy_vault.

### Files likely to touch
- `src/domain/wiki/store.py` (`scaffold`, optional `scrub_empty_seed_taxonomy`, maybe `cleanup_vault`)
- `tests/unit/wiki/test_vanilla_wiki_seeding.py`
- `tests/unit/wiki/test_wiki_store.py` (scrub regression)
- Possibly `src/web/routers/settings.py` / boot only if scrub must be explicit flag
- Docs/card note under `.github/cards/` or CHANGELOG

---

## Investigation confidence

- Historical mkdir list == Jacob’s list: **Certain** (`git show 69c8ceb7^:src/domain/wiki/store.py`).  
- Tip no longer creates them on empty vault: **High**.  
- Leftover empty dirs explain “on scaffold” without new mkdir: **High**.  
- Live Jarvis vault contents not listed this session: confirm when implementing.
