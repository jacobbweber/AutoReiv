---
id: CARD-468
title: "Agent display name drifts between AppData pack.json and the DB agent record"
status: Ready
created: 2026-09-24
branch: qa
related:
  - CARD-467
  - CARD-455
  - CARD-449
  - CARD-443
labels:
  - type:bug
  - area:agents
  - area:packs
  - P3
---

# [CARD-468] Agent display name drifts between AppData pack.json and the DB agent record

> **Status**: Ready
> **Created**: 2026-09-24
> **Observed during**: CARD-467 - live `%LOCALAPPDATA%\AutoReiv\packs\developer\pack.json` said `"name": "Super Developer"` while the DB (`custom_agents` and `agent_overrides`, updated 2026-09-24 7:01 PM ET) and `GET /api/agents/developer` said `Developer`. CARD-455's failing test read the pack.json name because a fresh test DB rebuilt the profile from the file.
> **Related**: CARD-467 (test isolation that exposed it), CARD-455 (absorbed), CARD-449 (content lock), CARD-443 (promotion; SQLite is the sole profile writer)
> **Labels**: `type:bug`, `area:agents`, `area:packs`, `P3`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine - **still no product code** |
| **`build`** | Pick the source of truth and make rename write/reconcile both |
| **`merge to qa`** | After tests pass and live names match |

Do not write product code until Jacob says **build** on this card.

---

## 1. Four Beats

### Beat 1: What Jacob means

An agent has one name. If I rename it in Agent Studio (or it is renamed any other way), every place that shows or rebuilds that agent uses the same name. I prefer simple one-word names (Developer, Tutor).

### Beat 2: What AutoReiv does now

1. The display name is stored three times: AppData `packs/<id>/pack.json` `name`, DB `custom_agents.name`, and DB `agent_overrides.name` (builtin/platform agents).
2. Agent Studio save (`PUT /api/agents/{agent_id}` in `src/web/routers/agents.py`) writes only the DB (`save_agent_override` for platform/builtin agents, `register_custom_agent` + override mirror for others). It never updates `pack.json`.
3. Serve reads the DB, so the live UI and API show the DB name. But anything that builds a profile from the pack folder with an empty DB (fresh install, restore to a new data dir, a test DB, the declarative reconciler on first boot) reads `pack.json` and resurrects the old name.
4. Nothing reports the mismatch. The same drift exists for other mirrored fields: live Developer `pack.json` `system_prompt` is a 61-character legacy line while the DB holds the real 1,538-character prompt (platform prompt plus Jacob's "Always follow SOLID and DRY principles.").
5. On 2026-09-24 (CARD-467 merge) the live Developer `pack.json` name was hand-corrected to `Developer` (backup `backups\developer-pack.json-pre-rename-20260924-213742.json`).

### Beat 3: What will change

1. Single source of truth: the DB agent record (override for platform/builtin agents, `custom_agents` otherwise) owns the display name, matching ADR-0056 / CARD-443 ("SQLite is the sole writer for profiles"). `pack.json` `name` becomes a mirror.
2. Agent Studio rename (and every other DB name write, e.g. reset/restore from CARD-450) also writes the new name into AppData `pack.json`, atomically (temp file + replace), leaving every other key and the file's formatting intact.
3. Startup reconcile: when the DB has a record and `pack.json` `name` differs, rewrite `pack.json` `name` from the DB and log it once. When the DB has no record (fresh install), `pack.json` seeds the DB as today.
4. The name change does not set the CARD-449 content lock by itself (name is a scalar, like max_turns/model).
5. Decision for Jacob at `continue`: should the same mirror rule apply to `system_prompt` in `pack.json`, or should that key be dropped from AppData `pack.json` entirely since the DB owns it?
6. Tests:
   - Rename via `PUT /api/agents/developer` updates DB and AppData `pack.json` `name`; other pack.json keys unchanged; `user_modified` unchanged by a name-only save.
   - Same for a non-platform custom pack agent.
   - Startup reconcile fixes a seeded mismatch (`pack.json` "Super Developer", DB "Developer") and leaves the DB value.
   - Fresh DB + `pack.json` name still seeds the DB.
   - Reset/restore (CARD-450) keeps `pack.json` name in step.

### Beat 4: What dies

1. Studio rename that updates only the DB.
2. Silent name drift between AppData `pack.json` and the DB.

---

## 2. Acceptance criteria (EARS)

- **[REQ-468-001]** WHEN an agent's display name is saved through the agents API, THE SYSTEM SHALL write the same name to the DB agent record and to AppData `packs/<id>/pack.json` when that file exists.
- **[REQ-468-002]** WHEN serve starts and a DB agent record exists whose name differs from its AppData `pack.json` name, THE SYSTEM SHALL rewrite the `pack.json` name from the DB and leave the DB unchanged.
- **[REQ-468-003]** WHEN no DB record exists for a pack, THE SYSTEM SHALL keep seeding the name from `pack.json`.
- **[REQ-468-004]** WHEN only the name changes, THE SYSTEM SHALL NOT set the CARD-449 content lock.

---

## 3. Human Verification Runbook (under 2 minutes)

1. In Agent Studio rename Tutor to `Tutor2`, save.
2. `Select-String '"name"' "$env:LOCALAPPDATA\AutoReiv\packs\tutor\pack.json" | Select -First 1` shows `Tutor2`; `GET /api/agents/tutor` shows `Tutor2`.
3. Rename back to `Tutor`; both show `Tutor`. Platform Defaults badge unchanged by the rename.

---

## 4. Constraints

- Docs-only until **build**. Never rewrite AppData files during tests (CARD-467 isolation applies).
