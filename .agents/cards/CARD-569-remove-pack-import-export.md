---
id: CARD-569
title: "Remove agent pack import/export and the pack builder"
status: Ready
created: 2026-09-28
branch: fix/card-569-remove-pack-import-export
related:
  - CARD-570
  - CARD-568
labels:
  - type:chore
  - area:agents
  - P1
needs_decision: none
milestone: M25
proof: "guard test tests/unit/agent_packs/test_card569_no_pack_import_export.py; ruff clean; fast preflight --base qa GREEN; not-slow suite with only the 3 known card354 failures; live: health on both addresses, Agent Studio loads, per-agent tool counts compared with 26/0/33/20/43"
---

# [CARD-569] Remove agent pack import/export and the pack builder

> **Status**: Ready
> **Related**: CARD-570 (agents and skills load from platform/, the rest of the pack removal), CARD-568 (flat tool lists removed)
> **Labels**: `type:chore`, `area:agents`, `P1`

## Why

Agents are now agents -> skills -> tools, and full data-folder backups exist, so there is no need to package an agent as a pack (zip) to export, import or scaffold it. This is the first, self-contained slice of the pack removal (plan: `scratch/pack-removal-plan.md`, research: `scratch/research-comparison.md`). Dev-only until 1.0: no compatibility paths.

## Change

1. **API**: delete `GET /api/agents/{agent_id}/pack.zip` and `POST /api/agents/import-pack` (`src/web/routers/agents.py`).
2. **UI**: remove the Import pack / Export pack buttons and the file input from Agent Studio (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`).
3. **Pack builder tools**: remove `export_agent_pack`, `import_agent_pack`, `scaffold_agent_pack` (`src/application/skills/agent_pack_tools.py`) and `propose_agent_specification` (`agent_builder_tools.py`), their skill-tool table entries (`agent_packs/schema.py`), tool-policy and observability mentions. `inspect_agent_pack` is useful to the agent-authoring skill (read an agent's tools and skills), so it becomes `inspect_agent` (reads the agent profile only, no pack.json fallback).
4. **Pack builder skills**: delete `src/infrastructure/skills/seeds/build-agent-pack/` and `platform-packs/autoreiv/skills/build-agent-pack/`, drop `build-agent-pack` from the AutoReiv pack. Rewrite `seeds/proposals/SKILL.md` and `autoreiv/skills/agent-authoring/SKILL.md` so a new agent is created in Agent Studio, not by a pack tool.
5. **Pack service**: remove export (folder/zip/fleet), zip import, fleet import and scaffold from `AgentPackService`. The folder import used by platform-pack install at boot stays until CARD-570 deletes it.
6. **Pack MCP server**: delete `src/infrastructure/mcp/pack_server.py`, `mount_agent_pack_server` / `unmount_agent_pack_server` in `client_adapter.py`, and the pack MCP config models if nothing else uses them.
7. **Tests**: delete or trim the tests of the removed pieces (import/export, scaffold, pack tools, pack server, pack API, commit/scaffold routes in proposals tests, frontend pack buttons). E2E: no journey calls the pack routes (checked: only `smoke.spec.js` mentions keep-customizations, which is CARD-570).
8. **Guard**: `tests/unit/agent_packs/test_card569_no_pack_import_export.py`: the removed routes, tools, skill folders and module are gone.

## Out of scope (CARD-570)

pack.json and its schema, platform-pack promotion/seeding, keep-customizations, per-agent backups, the platform-defaults panel, DB agent tables, the data-dir wipe.

## Done when

- The two routes return 404/405, the Studio has no Import/Export buttons, and no agent has a pack builder tool.
- `rg 'export_agent_pack|import_agent_pack|scaffold_agent_pack|propose_agent_specification|inspect_agent_pack|pack_server|import-pack|pack\.zip' src platform-packs tests/e2e` finds nothing.
- Resolved tools per agent: unchanged except AutoReiv, which loses exactly the removed pack builder tools (report the count).
- Guard test passes, ruff clean, fast preflight `--base qa` GREEN, full not-slow suite with only the 3 known card354 failures, live check done.
