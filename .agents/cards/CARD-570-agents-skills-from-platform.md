---
id: CARD-570
title: "Agents and skills load from platform/ with user copies in the data dir (remove agent packs)"
status: In Review
created: 2026-09-28
branch: fix/card-570-agents-skills-from-platform
related:
  - CARD-569
  - CARD-568
  - CARD-539
labels:
  - type:refactor
  - area:agents
  - P1
needs_decision: none
milestone: M25
proof: "guard test tests/unit/agents/test_card570_no_packs.py plus loader/override/tools-validation tests; ruff clean; fast preflight --base qa GREEN; full not-slow suite per CARD-560 rules; backup verified (count+size), data dir wiped, fresh start, per-agent tool and skill counts compared with the pre-wipe record; live Agent Studio edit/Use shipped version/hide check"
---

# [CARD-570] Agents and skills load from platform/ with user copies in the data dir

> **Status**: Ready
> **Related**: CARD-569 (pack import/export and pack builder removed first), CARD-568, CARD-539 / ADR-0061
> **Labels**: `type:refactor`, `area:agents`, `P1`

## Why

An agent is defined in up to four places today (pack.json copied into AppData and promoted by hash, a DB profile row, a DB override row, and about 10 promotion settings keys), and a skill's tools in four more. The agreed design (Jacob, 2026-09-28; plan `scratch/pack-removal-plan.md`, research `scratch/research-comparison.md`) keeps shipped content in the repo, puts user edits in plain files in the data dir, and removes the "agent pack" concept entirely. Dev-only until 1.0: no migrations, the data dir is wiped at the end.

## Design (agreed)

1. **Shipped content is read in place** from the repo:
   - `platform/agents/<id>.md`: frontmatter (name, description, tone, purpose, avatar, show_in_chat, max_turns, skills: [ids]) + system prompt as the body.
   - `platform/skills/<id>/SKILL.md`: frontmatter with `tools:`. **That list is the only skill -> tool list** (no pack.json skills[].tools, no code tables `PLATFORM_SKILL_TOOLS` / `DYNAMIC_SKILL_TOOLS`, no `skill_bindings` table, no second copy in `tool_skill_resolver.py`).
   - Merge `platform-packs/*/skills` and `src/infrastructure/skills/seeds/` into `platform/skills/` (one flat namespace; identical duplicates merged; `socratic-tutoring` and `mcp-engineering` differ: keep the Tutor and Developer versions).
2. **User copies win by id**: saving an agent or skill in a Studio writes the full file to data `agents/<id>.md` or `skills/<id>/SKILL.md`. No field merging. The copy stores `based_on: <shipped hash>`; when the shipped file's hash differs, Studio shows "The shipped version changed since you edited this." with **Use shipped version** (deletes the copy).
3. **Deleting a shipped item hides it** (persisted, e.g. `agents/.hidden.json` / `skills/.hidden.json`); deleting a user-created item removes its file.
4. **Shipped ids are reserved**: a new custom agent or skill cannot take a shipped id.
5. **tools: lists are validated on load**: an unknown tool id is a visible warning (Studio and health details) and grants nothing; a test fails if a shipped skill names an unknown tool.
6. **Runtime-built tools** move from the settings key to data `tools/` and keep today's gates (tool check before save, subprocess sandbox, ToolPolicyGate), plus an **approved-code hash** (a changed file is not mounted until re-approved) and an **enable flag only Jacob can flip** (agents can propose, never enable).
7. **Agent edits that add tools to a skill become proposals** Jacob approves (a permission change under ADR-0061); prose-only edits may stay direct.
8. **Per-agent model/provider** stay separate settings, not in the agent file; "Use shipped version" keeps them.
9. **DB holds only chats and settings**: drop `agent_overrides`, `custom_agents`, `skill_bindings` and the `platform_*` settings keys. Agent memory moves to `agents/<id>/memory.db`.
10. `resolve_allowed_tools` stays the single permission decider (ADR-0061); it reads the winning SKILL.md `tools:` list.

## Change

- **Delete**: `platform_pack_promotion.py`, `platform_packs.py`, the rest of `agent_packs/service.py` and the pack schema (`AgentPackManifest`, `PACK_SCHEMA_VERSION`, FleetManifest, `REJECTED_TOOL_LIST_KEYS`), `reconciler.py`, `seed.py`, `legacy_pack_tools.py`, `max_turns_upgrade.py`, `skill_bindings.py`, keep-customizations (`/api/settings/platform-pack-keep-customizations`, Settings toggle), per-agent content backups and restore, `/api/platform-packs/sync(-status)`, `accept-platform-seed`, the platform-defaults badge and reset panel (`forge/platform_defaults.js`), `platform-packs/`, data `packs/`.
- **Rewrite**: registry loader (repo then data dir), `resolve_allowed_tools` / `skill_tools`, Agent Studio save / Use shipped version / hide / "shipped changed" note, Skill Studio / workshop / distillation / proposal write paths to data `skills/`, skill catalog (tiers `platform` and `user`; `user-packs` routes and `list_user_skill_packs` renamed to skills), Tools Studio "attach tool to skill" (edits the skill's tools through a proposal), memory DB path, resolver/backup/migrate without `packs_path`.
- **Rules / docs**: new ADR "Agents and skills are files; no packs" (supersedes the pack parts of ADR-0048/0056/0058, note in ADR-0061); rules: **no old-format readers before 1.0** (a format change comes with a wipe or Use shipped version) and **a skill is a job that groups several tools, not one skill per tool; short instructions are fine for obvious tools; the skill's tools list shapes what the model sees, the permission check and the tools themselves are the safety**. Update `README.md`, `.agents/rules/boundaries.md`, boundary-audit script, `docs/education/tutor-learning-os-inventory.md`.
- **Tests**: delete pack/promotion/seeding/keep-customizations/backup/badge tests; add loader tests (shipped only, user copy wins, Use shipped version, hide persists, reserved ids, shipped-changed note), tools-validation test (shipped skills name only known tools), runtime-tool approval-hash test; update fixtures that write pack.json. Guard `tests/unit/agents/test_card570_no_packs.py`: `pack.json`, `platform-packs`, `agent_pack`, `keep_customizations`, `skill_bindings` appear nowhere in `src/`.

## Data wipe (Jacob pre-approved, including the wiki)

1. Record per-agent tools and skills (`/api/agents/<id>`) and non-secret settings, as in CARD-568.
2. Stop serve; copy `C:\Users\jacob\AppData\Local\AutoReiv` to `C:\Users\jacob\AppData\Local\AutoReiv-backup-<YYYYMMDD-HHMM>`; check file count and size match; never delete it.
3. Wipe the data dir contents (database incl. -wal/-shm and vault key, agents, backups, migrations, packs, skills, templates, wiki).
4. Start serve from the branch; restore non-secret model/provider settings; health on 127.0.0.1:8000 and 192.168.1.99:8000.
5. Per-agent tool and skill counts match the record (differences explained). Not touched: the repo's other data, `scratch\live_qa_data`, the Spark and Nimo machines.

## Done when

- No pack concept remains (guard green); shipped agents/skills load from `platform/`; user copies in data `agents/` / `skills/` win by id; Use shipped version, hide and reserved ids work; unknown tools warn and grant nothing.
- DB has no agent/skill definition tables; memory DBs live in `agents/<id>/memory.db`.
- Runtime tools live in data `tools/` with approval hash and Jacob-only enable.
- Checks: ruff clean, fast preflight `--base qa` GREEN, full not-slow suite per CARD-560; backup verified, wipe and fresh start done, counts compared; live check in Agent Studio (edit an agent, see "Edited", Use shipped version; hide and unhide a skill).

## Results (2026-09-28, In Review)

- Commits on `fix/card-570-agents-skills-from-platform`: a180e5c4, 6dc623db, 87f96b30 (+ this card update). vs qa: 243 files, +2351 / -12897 lines.
- Shipped agents (`platform/agents/*.md`, 5) and skills (`platform/skills/*/SKILL.md`, 44) are read in place; user copies in data `agents/` / `skills/` win by id (`based_on` hash for "shipped changed"); `.hidden.json` hides shipped items; shipped ids are reserved. Packs, seeds, reconciler, skill_bindings, keep-customizations, platform-defaults UI removed; `agent_overrides` / `custom_agents` / `skill_tool_bindings` tables dropped; memory at `agents/<id>/memory.db`.
- ADR-0062 (note in ADR-0061); rules "no old-format readers before 1.0" and "a skill is a job" in `.agents/rules/boundaries.md`. Guards: `test_card570_no_packs.py`, `test_card539_single_allowed_tools.py` (adapted); loader tests `test_card570_agent_skill_files.py`; vitest `card570_file_status.test.js`.
- Checks: ruff clean; not-slow suite 2012 passed / 18 skipped / 3 failed (known test_card354 2/4/5 severity); vitest 940 pass; fast preflight `--base qa` RED only because the changed `test_card354_developer_simulations.py` (skill paths updated) brings its 3 known failures into "changed tests"; all other stages green.
- Wipe: backup `C:\Users\jacob\AppData\Local\AutoReiv-backup-20260928-2304` (81 files / 1,504,221 bytes, matches source); data dir wiped (wiki included); fresh start from branch; vllm provider (base URL, default model qwen3.8-27b-fp8), purpose matrix and 5 vision overrides restored. No stored credentials existed. Per-agent model/provider were all `default`.
- Counts after fresh start (tools/skills): developer 26/11, direct 0/0, tutor 33/7, architect 20/5, autoreiv 39/11 — match.
- Live: edit tutor -> user copy wins (`source: user, edited`); Use shipped version -> removed; delete architect -> hidden across restart, unhide restores; custom agent id `developer`/`architect` -> 409; data skill naming `c570_no_such_tool` -> health warning, tool not granted; skill hide/unhide works.
- Round 2 (2026-09-28, finish in-area scope): commits 44736ecc, 76eb7ad1, 24ccb294, 944a521a, 4d276038, 1ea25417 (+ this card update).
  - Runtime-built tools are files in data `tools/<name>/` (`tool.py` + `tool.json`); `tools/.approvals.json` holds `{enabled, approved_sha256}`. Mounted only when enabled and the code hash matches; changed code -> `needs_reapproval`, not mounted, invoke 409. Enable/disable only via `POST /api/tools/native/{name}/enable|disable` (Tools Studio "Runtime-built tools" panel); no agent tool calls it (guard test). The `native_custom_tools` setting is gone.
  - Agents cannot grant tools: a skill save during an agent tool call keeps the file but turns each added tool into a pending `attach_tool_to_skill` proposal (store skill-write guard). Choice: Jacob's own Skill/Agent Studio saves (HTTP, no tool context) save directly - he is the approver, so a proposal would ask him to approve himself.
  - Renames: `user-packs` -> `user-skills` routes, `list_user_skill_packs` -> `list_user_skills`, `commit_skill_pack` -> `commit_skill`, `pack_id` -> `skill_id`; `requires_tools` -> `tools` (UI, API, frontmatter; no old reader); `tests/unit/agent_packs` -> `tests/unit/agent_skills`; `AgentOrigin.PACK` -> `FILE`, tiers `platform|user`. Guard `test_no_pack_wording_in_src_or_shipped_content` scans src + platform. History docs (ADRs, archive, findings entries naming old ids) left as history.
  - card354 simulations 2/4/5 use a self-contained tmp project + 16 KB `sentinel.db` fixture; findings line removed.
  - Settings restored from backup: projects_root `D:\Projects\Exprimentation\`, selected_project agentic-test, tool_policy (empty lists, already equal).
  - Live DB: `scaffold_spine` (column `pack_id` -> `skill_id`) and `skill_binding_meta` (tier default) were empty and dropped so they are recreated with the new schema (DB copy `autoreiv.db.pre-card570-scaffold.bak`).
  - Checks: ruff clean; not-slow suite 2021 passed / 18 skipped / 0 failed; vitest 940 pass; fast preflight `--base qa` GREEN.
  - Live: health ok on 127.0.0.1:8000 and 192.168.1.99:8000; counts developer 26/11, direct 0/0, tutor 33/7, architect 20/5, autoreiv 39/11; tutor edit -> user copy, use-shipped restores; architect delete hidden across restart, unhide; `developer` id -> 409; unknown-tool skill -> health warning (cleared after removal + restart); skill hide/unhide; runtime tool: register -> saved not mounted (invoke 409) -> enable -> mounted (reaches skill policy, fail closed) -> new code -> needs_reapproval (409) -> delete; `/api/skills/user-skills` 200.
  - Test steps added: Tools Studio > Runtime-built tools: Enable a saved tool; after its code changes it shows "Approve new code"; a tool an agent adds to a skill appears as a pending proposal, not on the skill.
  - Limitation: no user auth in AutoReiv, so a process on this machine with shell/HTTP access could call the localhost enable route; no agent tool exposes it.

## Log

- 2026-09-28: Built per agreed design; wipe + fresh start done; moved to In Review.
- 2026-09-28: Round 2: runtime tools with Jacob-only enable + hash, agent tool grants as proposals, pack renames + wording guard, card354 fixture, settings restored; still In Review.
