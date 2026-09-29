---
id: CARD-568
title: "Full cleanup of old tool-list leftovers (profiles, DB columns, Studio, settings, migration, UI, tests) on a fresh data dir"
status: Ready
created: 2026-09-28
branch: fix/card-568-remove-tool-list-leftovers
related:
  - CARD-541
  - CARD-539
labels:
  - type:chore
  - area:agents
  - P1
needs_decision: none
milestone: M25
---

# [CARD-568] Full cleanup of old tool-list leftovers on a fresh data dir

> **Status**: Ready
> **Related**: CARD-541 (packs and pack schema already clean), CARD-539 / ADR-0061 (tools come only from ticked skills)
> **Labels**: `type:chore`, `area:agents`, `P1`

## Why

Since CARD-539 an agent's tools come only from `resolve_allowed_tools` (required platform tools plus the tools of ticked skills). CARD-541 removed the flat lists from the shipped packs and the pack schema, but `allowed_tool_names` / `pack_tool_names` still exist in about 120 files (about 480 references): they grant nothing, can drift, and confuse anyone reading an agent or the code. Jacob approved wiping his AutoReiv user data for this card, so there is no need to migrate old rows. The app can start from a fresh data dir, and the migration path goes away.

## Change

Remove every flat tool list, so that the only way to give an agent a tool is to tick a skill:

1. **Agent profile model**: drop `allowed_tool_names` and `pack_tool_names` from `AgentProfile` (`src/domain/kernel/models.py`) and `AgentCustomization` (`src/domain/settings/models.py`), plus every reader/writer: `src/infrastructure/agents/registry.py`, `src/domain/agents/guardrails.py`, `src/application/agent_packs/skill_list.py`, `src/application/agent_packs/service.py`, `src/application/skills/agent_pack_tools.py`, `src/cli/main.py` (show the resolved tool count instead).
2. **Database**: remove the `allowed_tools_json` and `pack_tools_json` columns from `agent_overrides` and `custom_agents` (`src/infrastructure/memory/schema.py`) and from `src/infrastructure/memory/repositories/settings.py`. No ALTER/copy migration: a fresh DB is created with the new schema.
3. **Agent Studio API**: drop the fields from the agent GET/PUT bodies and the models in `src/web/routers/agents.py`. A PUT that still sends them gets a clear 422 (or they are ignored with a logged note; pick one and test it).
4. **Settings**: remove the tool-list parts of the customization / keep-customizations code (`src/application/settings/settings_service.py`, `src/web/routers/settings.py`).
5. **Platform promotion and seeding**: `src/infrastructure/skills/platform_pack_promotion.py` and `platform_packs.py` stop reading or writing profile tool lists (`seed_pack_tools`, `_seed_tools_removed`, `new_pack_tools`, `final_tools`). The CARD-541 schema compat (`LEGACY_TOOL_LIST_KEYS`, ignore-with-note on import) stays, so old pack zips still import.
6. **capability_migration**: delete `src/application/agent_packs/capability_migration.py` and its callers, plus the `migrations/card-539-allowlists.json`-style migration writer. Fresh data has nothing to migrate.
7. **Frontend**: remove the `pack_tool_names` / `allowed_tool_names` "tool list" labels in `src/web/static/modules/studios/forge/platform_defaults.js`, and the "platform tool list" wording in the reset dialog (replaced list becomes: system prompt, shipped skill files, skill on/off list).
8. **E2E journeys**: stop sending `pack_tool_names` in the PUT body (`tests/e2e/journeys/card-563-*.mjs`, `card-564-*.mjs`, `card-566-*.mjs`), and have `card-520-teach-needs-tool.mjs` read the resolved `allowed_tools` instead of the flat lists.
9. **Fixture**: remove `tests/fixtures/card497/build-agent-pack.shipped-1f6a64cf.SKILL.md` or drop its tool-list line, and update the card497 test that reads it.
10. **Tests**: update or delete the roughly 95 test files that set or assert the flat lists (a repo-wide `rg 'allowed_tool_names|pack_tool_names'` lists them); assert resolved tools instead.
11. **Docs**: ADR-0061 gets a short "flat lists removed (CARD-568)" note; the build-agent-pack SKILL.md seeds keep only the "never write a flat tool list" line. Archived specs under `docs/archive_artifacts/` are left as history.
12. **Guard**: extend `tests/unit/agent_packs/test_card541_no_pack_tool_lists.py` (or add a CARD-568 guard) so that `allowed_tool_names` / `pack_tool_names` / `allowed_tools_json` / `pack_tools_json` appear nowhere in `src/`, `platform-packs/` or `tests/e2e/`. The only exception is the named import-compat constant in `schema.py`.

## Data wipe (Jacob approved; do it only inside this card, after the backup)

Configured data dir: `C:\Users\jacob\AppData\Local\AutoReiv` (from `/api/data-dir`, about 13 MB on 2026-09-28).

**Backup first (required, before anything is wiped):**
1. Stop serve.
2. Copy the whole folder to `C:\Users\jacob\AppData\Local\AutoReiv-backup-<YYYYMMDD-HHMM>` (outside the data dir, all files including hidden ones).
3. Check that the copy's file count and total size match the original. Record the backup path in this card's Results.
4. Never delete the backup in this card.

**Wiped (the whole contents of the data dir):**
- `database\autoreiv.db` (all settings, agents, overrides, custom agents, chats, jobs, education data, model/provider settings, keep-customizations)
- `database\.vault_key` (stored secrets can't be read without it; re-enter provider keys after the fresh start)
- `agents\`
- `backups\`
- `migrations\` (`card-539-allowlists.json`, `card-544-autoreiv-skills.json`, `card-550-developer-skills.json`)
- `packs\` (architect, autoreiv, developer, direct incl. the leftover `"pack_tool_names": []`, get_weather, get-weather, tutor, `autoreiv.zip`, `tutor.zip`)
- `skills\` (build-agent-pack, coordination, education-*, ipmi_read_temperatures, proposals, sandbox, sqlite-storage, wiki, worker, `_friction_recommendations.json`)
- `templates\` (`jobs`)
- `wiki\` (22 files). After the fresh start, copy the wiki notes back from the backup; they are Jacob's notes, not tool-list data.

**Not touched:** the repo checkout, `scratch\live_qa_data` (separate throwaway QA data), anything outside `C:\Users\jacob\AppData\Local\AutoReiv`, and the backup folder.

**After the wipe:**
1. Start serve so it creates a fresh data dir.
2. Re-enter the model/provider settings (Spark / Nimo) from the backup's values.
3. Restore `wiki\` from the backup.
4. Check health on 127.0.0.1:8000 and 192.168.1.99:8000.
5. Check that every platform agent (AutoReiv, Tutor, Direct, Developer, Architect) resolves the same tools as before (record the tool counts from `/api/agents/<id>` before the wipe) and that the Direct pack.json has no `pack_tool_names`.

## Done when

- `rg 'allowed_tool_names|pack_tool_names|allowed_tools_json|pack_tools_json'` finds nothing in `src/`, `platform-packs/`, `tests/e2e/` or `tests/fixtures/`, apart from the named import-compat constant.
- The DB schema has no tool-list columns, and there is no capability_migration code.
- An old pack zip with a flat list still imports, with the list ignored and noted.
- The backup exists and matches the original. The data dir was wiped and recreated fresh, and the model settings and wiki were restored.
- Resolved tools per platform agent are unchanged against the pre-wipe counts.
- The guard test passes, ruff is clean and fast preflight `--base qa` is GREEN. The full suite runs per CARD-560 rules.
- A short live check covers Agent Studio for each platform agent (skills and tools shown, save works, reset dialog wording) and one chat turn with AutoReiv.
