---
id: CARD-497
title: "Retire the Agent Training Factory (3/4): move Studio routes, delete the training loop backend, update packs"
status: Ready
created: 2026-09-25
branch: qa
related:
  - ADR-0060
  - CARD-495
  - CARD-496
  - CARD-511
  - CARD-512
  - CARD-498
  - CARD-520
  - CARD-521
  - CARD-472
  - CARD-418
  - CARD-421
labels:
  - type:cleanup
  - area:factory
  - area:backend
  - P1
---

# [CARD-497] Retire the Agent Training Factory (3/4): move Studio routes, delete the training loop backend, update packs

> **Status**: Ready (refined on `continue`, 2026-09-26 ~9:50 AM ET, from local qa `51b6402b`, with a fresh dependency sweep and a scratch reproduction). Decisions D1-D14 are to confirm at `build`. The remedy rename (old D3) moves to successor card CARD-520.
> **Created**: 2026-09-25
> **Governing ADR**: [ADR-0060](../adr/0060-retire-the-agent-training-factory.md) (Accepted). This card is step 4 of 6: CARD-495 (Done), CARD-496 (Done), CARD-511 (Done), **CARD-497**, CARD-512, CARD-498.
> **Series**: CARD-495, CARD-496, CARD-511, **CARD-497**, CARD-520 (split from this card), CARD-512, CARD-498
> **Labels**: `type:cleanup`, `area:factory`, `area:backend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first on `feat/card-497-factory-backend` |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** The server no longer runs, exposes or advertises a training factory. Every way AutoReiv trains, teaches and improves agents today keeps working: gap recording and the Agent Studio backlog, Skill Studio, Tools Studio with Developer and the CARD-511 check, Teach, Observability, ACE and memory. The Skill Studio routes that happen to live under the Factory move to Studio names.

**Beat 2: What AutoReiv does now** (checked on qa `51b6402b`, scratch server `scratch\c497_repro.py`, evidence `scratch\c497_repro_evidence.json`):
- **Background loop still runs.** `app.py` L336-348 builds a `FactoryOrchestrator` and starts it at L378 (polls every 2 s); L443-448 stop it. On scratch, `POST /api/agents/autoreiv/gaps/{gap}/train` (no UI caller) created job `fjob_...`, and the loop moved it to `blueprint` within 8 s.
- **Stranded gaps.** That call set the gap to `training`. The Agent Studio backlog lists only `pending` gaps (`forge/tools.js` L135), so the gap disappeared, and nothing but the Factory can ever move it on.
- **Factory router mixes two groups** (`routers/agent_training_factory.py`, 1,211 lines):
  - Skill and Tools Studio use `GET /capabilities` (L829), `POST /scaffold/runbook` (L897), `POST /scaffold/save` (L1011), `GET /skills` (L1170) and `GET /skills/{id:path}` (L1178). Frontend callers: `skill_studio.js` L254/L333/L377, `skill_authoring.js` L12, `skill_studio/skill_scope.js` L197, `skill_studio/workshop_meta.js` L164, `tools_studio_catalog.js` L545. All five worked on scratch (runbook generated, save wrote `skills/c497-demo/SKILL.md` under the scratch data dir, open returned the frontmatter).
  - Training only: `/jobs*` (L237-439, including promote), `/gaps` (L357) and `/phases/*` (L796-816).
- **Helpers.** `/scaffold/runbook` needs `agent_training_factory/llm.py` `phase_llm_text` (L953). `check_tool_collisions` (L16) is used **only by the promote route** (L510), which is deleted.
- **Chat tools.** `FactoryDispatchTools` (`application/skills/factory_dispatch_tools.py`, 334 lines) registers `launch_factory_training` and `inspect_agent_pack` (`infrastructure/agents/registry.py` L324-333). `platform-packs/autoreiv/pack.json` grants both (L93-94 in the `agent-authoring` skill and L164-165), and both show in the live catalog (105 tools on scratch). The `agent-authoring` SKILL.md tells AutoReiv to call `launch_factory_training` and watch "Factory Studio".
- **Stale Factory text elsewhere.** `build-agent-pack` SKILL.md L25 and L54 ("dedicated tools trained in the Factory", "Factory Studio owns training and wiring new callables"), in both `platform-packs/autoreiv/skills/` and `src/infrastructure/skills/seeds/`. Developer is allowed `build-agent-pack` but has no pack copy, so it reads `$DATA/skills/build-agent-pack/SKILL.md`. That seed copy is written only when missing (`seed.py` L67-84) and never updated, so Jacob's copy will keep the Factory text after this card unless the card refreshes it (D10).
- **Update-busy check.** `busy.py` L27, L52-55 and L122-140 add a Factory job checker. It is wired from `app.py` L357-358 and `routers/system.py` L41-42. Studio jobs are already counted separately (L103-120).
- **Auto-training leftovers (ADR-0060 D7).** `allow_autonomous_training` / `max_training_retries` are in the agents API (`routers/agents.py` L48-49, L166-167, L428-431), in pack export/import (`agent_packs/service.py` L210-211, L566-567, L599-600, L631-632), in `skill_list.py` L50-51, in the manifest schema (`schema.py` L565-566) and in the settings override (`registry.py` L157-160). No UI reads them. `JitToolSynthesizer` is built at `agent_kernel.py` L136-138 and never used. `KernelEventType.AUTO_TRAIN_PROGRESS` (`domain/kernel/models.py` L185, field L199) is never sent; `chat.py` L412-414 maps it.
- **Data layer.** `FactoryPacketRepository` (`infrastructure/memory/repositories/factory_packets.py`) is also a mixin on `SQLiteStateStore` (`sqlite_store.py` L12, L42). Its `save_job` / `list_jobs` / `delete_job` / `save_packet` / `list_packets` / `save_eval_run` are called only by Factory code (rg). `JobRepositoryMixin` comes first in the MRO, so `store.get_job` and `store.update_job_status` already resolve to Studio jobs. The tables are created in `schema.py` L380-445 and `connection.py` L125-131 and L247-248; `factory_phase_instructions` is created lazily by `prompt_registry.py` L170. Jacob's DB: 0 rows in every `factory_*` table and `scaffold_spine`, 1 pending gap, autoreiv pack not `user_modified`.
- **Remedy name.** `factory_escalation` is in distill output, Teach and Observability. It moves to **CARD-520**, together with a new finding: Observability's "Factory Escalation" card has an Apply button that always returns HTTP 500 (`tool_skill_resolver.apply_recommendation` L248 refuses anything but `runbook_patch`; `routers/observability.py` L419-424 turns that into a 500).

**Beat 3: What will change.**
1. **Move** the five Studio routes into a new `routers/skill_studio.py` (D4) with identical payloads, and switch the six frontend call sites in the same branch. The old paths answer **308** to the new ones for one release (D1); CARD-498 removes them. `phase_llm_text` moves to `application/skills/studio_llm.py` (D5). Save uses the app's data dir (D11).
2. **Delete** the training loop:
   - the `/jobs*`, `/gaps` and `/phases/*` routes and the gap `/train` route;
   - the orchestrator wiring in `app.py`;
   - `application/agent_training_factory/` (whole);
   - `factory_dispatch_tools.py`, `capability_graph.py`, `jit_synthesizer.py` (and its construction in the kernel), `tool_synthesizer.py`, `verification_battery.py` (whole, including the `detect_path_safety_violation` re-export CARD-511 left), `hyperv_tool_builders.py` and `skills/sandbox_runner.py`;
   - `domain/orchestration/factory_packets.py`, and the Factory repository with its store mixin (D7);
   - the Factory busy checker;
   - `AUTO_TRAIN_PROGRESS`, and the auto-training fields in the API and pack export (D9).
3. **Keep and move:**
   - `inspect_agent_pack` goes into `AgentPackTools` (D6), with the same tool id and grant.
   - Gap recording, listing, create and dismiss stay. Gaps stuck in `training` return to `pending` at startup (D8).
4. **Packs and skills:**
   - drop `launch_factory_training` from the autoreiv pack;
   - add it to `RETIRED_TOOL_NAMES` so persisted grants are purged (D12);
   - rewrite `agent-authoring` as intake that hands tools to Developer and skills to Skill Studio (D2);
   - remove the Factory lines from `build-agent-pack`, and refresh an unedited data-dir seed copy (D10).
5. **Data stays** for CARD-498: tables, rows, CREATE and column migrations are untouched (D7).

**Beat 4: What gets removed today.** The autonomous training loop and its background runner, the Factory job, gap, phase and train endpoints, the `launch_factory_training` chat tool, the unused JIT tool synthesizer and auto-training settings in the API, and about 9,600 lines of Factory-only code (10,005 lines in the delete set, less about 385 that move) with their tests. Nothing Jacob uses in the UI goes away; old Skill Studio URLs keep working for one release through redirects.

### What keeps training, teaching and improving agents (must not regress)

| Lane | Path after CARD-497 | Touched here? |
|---|---|---|
| Record a gap | Kernel `CapabilityDetector` (`agent_kernel.py` L1117, L1541) + `POST /api/agents/{id}/gaps` | No |
| Act on a gap | Agent Studio backlog: Open in Skill Studio, Ask Developer, Dismiss (CARD-496) | D8 only (stuck `training` gaps come back) |
| Write a skill | Skill Studio: capabilities, runbook, save, open | Routes move (D4) |
| Build a tool | Developer native / MCP lanes, CARD-511 check, Tools Studio | No |
| Teach | Distill: runbook Adopt, or needs-tool Ask Developer (CARD-472) | No (rename is CARD-520) |
| Observability | Friction runbook patches (Apply), architectural proposals | No (escalation fix is CARD-520) |
| Learn from sessions | ACE online + skill-eval sleep routine (`ace_online.py`, `skill_proposals.py`), reflexion, memory | No; they import nothing deleted (rg) |
| Build or package an agent | Agent Studio, `build-agent-pack`, `scaffold_agent_pack` | Text fix only (D10) |

## 2. Acceptance criteria (EARS)

- **[REQ-497-001]** WHEN the app starts, THE SYSTEM SHALL NOT create, start or stop a `FactoryOrchestrator`, and `app.state` SHALL have no `factory_orchestrator` or `factory_repo`.
- **[REQ-497-002]** Requests to `/api/agent_training_factory/jobs` (all methods and sub-paths), `/api/agent_training_factory/gaps`, `/api/agent_training_factory/phases/*` and `POST /api/agents/{id}/gaps/{gap}/train` SHALL return 404.
- **[REQ-497-003]** `GET /api/tools_studio/capabilities`, `POST /api/skill_studio/runbook`, `POST /api/skill_studio/save`, `GET /api/skill_studio/skills` and `GET /api/skill_studio/skills/{id}` SHALL return the same payloads as the old routes for the same input.
- **[REQ-497-004]** WHEN a client calls one of the five old Studio paths, THE SYSTEM SHALL answer 308 with the new path, keeping the method, body and query string. The redirects are removed in CARD-498.
- **[REQ-497-005]** WHILE Skill Studio and Tools Studio load, generate, save and open skills, THE SYSTEM SHALL request only the new routes. No file under `src/web/static` SHALL contain `/api/agent_training_factory`.
- **[REQ-497-006]** THE SYSTEM SHALL NOT register or offer `launch_factory_training`. On startup refresh and reconcile, it SHALL remove the tool from every stored grant, including `user_modified` packs and overrides.
- **[REQ-497-007]** `inspect_agent_pack` SHALL stay registered, granted to autoreiv, and return the same fields as before.
- **[REQ-497-008]** The shipped `agent-authoring` skill SHALL NOT mention the Factory or `launch_factory_training`. WHEN the operator asks for a new tool or MCP server, it SHALL hand off to Developer with a brief. WHEN they ask for a skill, it SHALL point to Skill Studio or `propose_skill`.
- **[REQ-497-009]** No shipped file under `platform-packs/` or `src/infrastructure/skills/seeds/` SHALL mention the Factory as current. WHEN the data-dir seed `skills/build-agent-pack/SKILL.md` matches a previously shipped version, startup SHALL replace it. WHEN it was edited, THE SYSTEM SHALL leave it unchanged and log one line saying so.
- **[REQ-497-010]** WHEN the app starts, gaps with status `training` SHALL become `pending` (idempotent). Gap create, list and dismiss, and kernel gap recording SHALL be unchanged.
- **[REQ-497-011]** The update busy check SHALL count chat streams, running routines and Studio jobs only. Its reasons SHALL never name the Factory.
- **[REQ-497-012]** The agents API and pack export SHALL NOT return `allow_autonomous_training` or `max_training_retries`. Requests and pack imports that still carry them SHALL be accepted and the fields ignored. `KernelEventType.AUTO_TRAIN_PROGRESS` SHALL NOT exist.
- **[REQ-497-013]** WHEN the app starts on a DB that has `factory_*` tables with rows, it SHALL start cleanly and leave those tables and rows unchanged (CARD-498 exports them).
- **[REQ-497-014]** No module under `src/` SHALL import a deleted module. The deleted files SHALL be absent. `tool_check.py` SHALL stay Factory-free.
- **[REQ-497-015]** The lanes in the table above SHALL keep passing their existing tests (Teach distill and Ask Developer, Observability runbook Apply, skill-eval sleep, Developer register with the CARD-511 check, gap backlog).

## 3. Decisions (recommendations; confirm at `build`)

| # | Decision | Recommendation |
|---|----------|----------------|
| D1 | Old Studio URLs | **Confirm: 308 redirects for one release** for the five moved routes only, keeping method, body and query; deleted in CARD-498. Reason: an open tab that has not been hard-refreshed (the phone especially) keeps calling old URLs, and 308 keeps a POST body. Removed training routes answer plain 404 |
| D2 | `agent-authoring` skill | **Confirm, with detail: rewrite as a Developer handoff and keep the skill id** (it is pinned in `allowed_skill`, three tests and Jacob's data). Title "Agent Capability Intake". Tools: `inspect_agent_pack`, `lookup_agents`, `handoff_to_agent`, `propose_skill`. The intake stays Socratic (target agent, goal, inputs, failure modes). Tool or MCP: hand off to `developer` with the brief (Tools Studio lane, CARD-511 check). Skill: Skill Studio or `propose_skill`. New agent: `build-agent-pack`. Alternative: retire the skill and rely on `build-agent-pack` plus handoffs, which loses capability intake for an *existing* agent |
| D3 | Remedy rename `factory_escalation` | **Revise: confirm `tool_escalation`, but move it to successor card CARD-520** together with the Observability Apply that always fails (new finding), which should become "Ask Developer" as in Teach. This keeps CARD-497 to backend removal plus one frontend URL switch. Readers there accept the old name in stored chat messages and recommendations |
| D4 | New route names | `GET /api/tools_studio/capabilities` (both Studios use it; it sits beside `/api/tools_studio/authoring`); `POST /api/skill_studio/runbook`; `POST /api/skill_studio/save`; `GET /api/skill_studio/skills`; `GET /api/skill_studio/skills/{id:path}`. All in a new `routers/skill_studio.py`. Payloads unchanged |
| D5 | Helpers | **Move** `phase_llm_text` to `application/skills/studio_llm.py` (only `/runbook` uses it). **Delete** `check_tool_collisions` with the promote route, its only caller. This revises the audit, which said to move both |
| D6 | Where `inspect_agent_pack` goes | **`application/skills/agent_pack_tools.py` (`AgentPackTools`)**, which already takes registry, store and data dir and sits next to export/import/scaffold pack tools. Same id, same grant, same output. This revises the location in ADR-0060 D4 ("next to the orchestration tools"; `OrchestrationTools` has no registry or data dir); add a one-line note to the ADR at `build` |
| D7 | Factory data layer | **Keep** the `factory_*` tables, their CREATE SQL and column migrations until CARD-498. **Delete** `FactoryPacketRepository`, its `SQLiteStateStore` mixin and `domain/orchestration/factory_packets.py`. CARD-498 exports with plain SQL (note added to CARD-498). Safe: only Factory code calls the mixin, and Studio `get_job` / `update_job_status` already win in the MRO |
| D8 | Gaps left in `training` | **At startup, set `training` gaps back to `pending`** (idempotent) so they reappear in the backlog, where Open in Skill Studio and Ask Developer act on them. Leave `trained` / `failed` / `cant` / `dismissed` alone. The status constants move from `gap_link.py` to the gap repository. Jacob has 0 such gaps; the scratch run shows how one gets stranded |
| D9 | Auto-training leftovers (ADR D7 detail) | Remove the fields from the agents API response and request model, pack export and `skill_list`; ignore them when present in requests and imported manifests. **Keep** the domain field, repository read/write and DB columns (no behaviour) until the CARD-498 column cleanup. Delete `AUTO_TRAIN_PROGRESS`, `KernelEvent.auto_train` and the SSE branch |
| D10 | Stale `build-agent-pack` seed in the data dir | Update both shipped copies. **Rewrite `$DATA/skills/build-agent-pack/SKILL.md` only when its hash matches a previously shipped version** (the same approach CARD-426 used for `native-tool-engineering`); log and skip edited copies. The general "seeds never update" issue is filed as CARD-521 |
| D11 | Save route data root | The moved `save` route uses the app's data dir (the helper `/skills` already uses), not a fresh `DataDirResolver()`. It gives the same result today (the scratch save landed in the scratch dir) and leaves one resolution path |
| D12 | Purge old grants | Add `launch_factory_training` to `RETIRED_TOOL_NAMES`. Pack refresh (`platform_pack_promotion.py` L770, L836-838, L894) and the seeder (`capabilities/seeder.py` L171-173) then strip it from stored profiles, including user-modified ones |
| D13 | Orphans found in the sweep | `orchestration/self_scaffold_queue_e2e.py` (no `src` caller, scaffold-spine family) goes to **CARD-512** (note added). `orchestration/honesty_smoke_pack.py` (CARD-261, not Factory) is left alone. `application/skills/workshop.py` and `runbook_frontmatter.py` stay; only their "Factory workshop" docstrings change |
| D14 | Slicing | **One branch for CARD-497**: the route move and the deletions share the router file and `app.py`. Split only the remedy rename and Observability fix into **CARD-520**. Suggested order after this card: CARD-520, then CARD-512, then CARD-498 |

## 4. Move, keep and delete lists

**Move**
- `routers/agent_training_factory.py` L829-1210 (capabilities, runbook, save, `_pin_saved_skill_on_agent`, skills, skill open, `_workshop_data_root`) into `routers/skill_studio.py` (D4).
- `agent_training_factory/llm.py` `phase_llm_text` into `application/skills/studio_llm.py` (D5).
- `FactoryDispatchTools.inspect_agent_pack` and its registration into `AgentPackTools` (D6).
- The gap status constants from `gap_link.py` into `repositories/capability_gaps.py` (D8).
- Frontend: `skill_studio.js` L254, L333, L377 (and header comment L5); `skill_authoring.js` L12; `skill_studio/skill_scope.js` L197; `skill_studio/workshop_meta.js` L164; `tools_studio_catalog.js` L545.

**Keep (unchanged or docstring only)**
- `application/skills/workshop.py`, `runbook_frontmatter.py` (docstrings), `capability_detector.py`, the gap repository and gap routes (except `/train`), `ace_online.py`, `skill_proposals.py`, `mid_job_self_scaffold.py` (used by the Job pipeline).
- `factory_*` tables, `schema.py` L380-471, `connection.py` L125-131 and L247-248 (D7); `scaffold_spine` (CARD-512).
- Skill Studio `factory*` element ids (ADR-0060 D5). `agent_packs/schema.py` `RETIRED_FACTORY_PERSONA_PACK_IDS` (history of retired persona packs).
- The `allow_autonomous_training` / `max_training_retries` domain fields and columns (D9).

**Delete**
- `src/application/agent_training_factory/` (20 files, 5,265 lines).
- `src/web/routers/agent_training_factory.py` after the move (L30-827 are training-only, including the promote-only helpers `_skills_from_files_map`, `_select_pack_files`, `extract_job_initial_inputs`), and its `include_router` (`app.py` L49, L601).
- `app.py` L336-348, L357-358 (busy wiring becomes store only), L378, L443-448, L498, L515-516.
- `src/web/routers/gaps.py` L12, L14, L39-46, L117-175.
- `src/application/skills/factory_dispatch_tools.py` and `registry.py` L324-333.
- `src/application/orchestration/capability_graph.py`, `jit_synthesizer.py`, `tool_synthesizer.py`, `verification_battery.py`, `hyperv_tool_builders.py`; `src/application/skills/sandbox_runner.py`.
- `agent_kernel.py` L136-138.
- `src/domain/orchestration/factory_packets.py`, `src/infrastructure/memory/repositories/factory_packets.py`, `sqlite_store.py` L12 and L42.
- `busy.py` factory checker (L27, L32, L51-55, L80-81 parameter, L122-134, L140); `routers/system.py` L41-42 parameter.
- `domain/kernel/models.py` L185 and L199; `chat.py` L412-414.
- `platform-packs/autoreiv/pack.json` L94 and L165 (`launch_factory_training`).
- `tool_check.py` docstring lines that name the deleted modules (keep the "Factory-free" rule, reworded).

## 5. Failing-tests-first plan

Write these first and see them fail, then build. Test numbers are referenced in the build evidence.

**New or changed contracts (must fail first)**
1. `tests/unit/web/test_skill_studio_routes.py`, capabilities: `GET /api/tools_studio/capabilities` has the same shape as today (`total_tools`, `namespaces`, `native_custom`, `legacy_pack_tool`, `origin_label`). Ported from `test_scaffolder_endpoints.py::test_get_factory_capabilities` and the oc423 catalog assertions.
2. The same file, runbook: `POST /api/skill_studio/runbook` returns the fallback runbook with no gateway, and the model text with a fake gateway (port `test_scaffold_runbook_generation`).
3. Save: `POST /api/skill_studio/save` writes the skill, binds SQLite and pins it when `agent_id` is given (port `test_scaffold_save_and_pin_skill`, `test_card_418_skill_studio_save.py`, `test_card_411_factory_skill_bindings.py`). It writes under `app.state.data_dir_paths` even when `AUTOREIV_DATA_DIR` points elsewhere (D11).
4. Skills list and open through the new routes (port `test_workshop_skill_resolve.py`, the oc426 skill read).
5. Each of the five old paths answers 308 to the new path; the method, body and query are kept (`?agent_id=` on skill open).
6. Removed routes return 404: `GET`/`POST /jobs`, `/jobs/{id}`, `/jobs/{id}/step`, `/jobs/{id}/promote`, `DELETE /jobs/{id}`, `/gaps`, `GET`/`PUT`/`DELETE /phases/...`, `POST /api/agents/{id}/gaps/{gap}/train`.
7. App startup: `app.state` has no `factory_orchestrator` / `factory_repo`, and the lifespan starts no Factory task (flip `test_dead_code_shims_scavenger_385.py::test_app_state_and_web_app_factory_orchestrator_cleanliness`).
8. `BusyDetector` / `make_store_busy_detector` take no Factory checker; the reasons never contain "Factory"; a queued Studio job still makes it busy.
9. Gaps: a `training` gap becomes `pending` on startup, a second start changes nothing, `trained` / `dismissed` are untouched, and create, list and dismiss behave as before (rewrite `test_gaps_api.py` without the train step).
10. Tool registry: `launch_factory_training` is not registered; `inspect_agent_pack` is registered by `AgentPackTools` with the same output (port the two inspect tests from `test_factory_dispatch_tools.py`).
11. Pack refresh and the seeder remove `launch_factory_training` from stored profiles, including a `user_modified` one; `RETIRED_TOOL_NAMES` contains it.
12. Contract: autoreiv `agent-authoring` tools are `inspect_agent_pack`, `lookup_agents`, `handoff_to_agent`, `propose_skill`; no file under `platform-packs/` or `src/infrastructure/skills/seeds/` contains `launch_factory_training` or "Factory Studio" / "trained in the Factory" (update `test_card_126_platform_packs.py` L48-54).
13. Seed refresh: an unedited old `build-agent-pack` seed is replaced on startup; an edited one is left alone and logged.
14. Agents API: `GET /api/agents/{id}` has no auto-training fields; `POST`/`PUT` bodies with them succeed; pack export omits them; importing an old manifest with them works.
15. `KernelEventType` has no `AUTO_TRAIN_PROGRESS`, and `chat.py` has no `auto_train_progress` SSE branch.
16. Import contract: an AST walk of `src/` finds no import of a deleted module, and the deleted paths are absent (extend `test_dead_code_shims_scavenger_385.py`). `test_tool_check.py` L212-217 changes from "the re-export is the same object" to "`verification_battery` does not exist".
17. Upgrade: a DB with `factory_*` rows starts the app cleanly, and the rows are still there afterwards.
18. **Vitest**: `skill_studio.js`, `skill_authoring.js` (`SILENT_RUNBOOK_URL`), `skill_scope.js`, `workshop_meta.js` and `tools_studio_catalog.js` call the new URLs; no static file contains `/api/agent_training_factory`. Update `card_418`, `card_420`, `card_421`, `card_423`, `card_411` and `card_496` (their old-URL assertions).
19. **Smoke TC-43** (desktop and phone): open Skill Studio, open an existing skill, Generate (fallback is fine), Save. Network shows only `/api/skill_studio/*` and `/api/tools_studio/capabilities`; `GET /api/agent_training_factory/jobs` returns 404. TC-34's "no Factory request after load" check (L1159, L1189) stays.

**Updated (URL only):** `test_oc423`, `test_oc425`, `test_oc426`, `test_oc429`, `test_oc431`, `tests/integration/test_mcp_disable_unmount.py` (capabilities or skills URL); `test_card_127_platform_skills_layout.py` and `test_skill_linter_consolidation.py` (the id stays, so they are likely unchanged).

**Deleted (ADR-0055, Factory-only):**
- `tests/unit/agent_training_factory/*` (17 files; the three scaffolder tests are ported in 1-3);
- `tests/unit/web/test_factory_api.py`, `test_agent_training_factory_router.py`;
- `tests/unit/routers/test_agent_training_factory_prompts.py`;
- `tests/unit/orchestration/test_factory_runner.py`, `test_factory_packets.py`, `test_capability_loop.py`, `test_phase_prompt_registry.py`, `test_verification_battery.py`, `test_tool_synthesizer.py`;
- `tests/unit/kernel/test_in_flight_synthesis.py`;
- `tests/unit/skills/test_factory_dispatch_tools.py` (the inspect tests are ported in 10), `tests/unit/skills/test_sandbox_runner.py`;
- `tests/integration/factory/test_dogfood_factory_pipeline.py` and `test_scaffolder_lifecycle.py` (ported in 1-3).
- `tests/integration/capabilities/test_dogfood_capability_gap_loop.py` keeps its first two tests (kernel records a gap, backlog lists it) and loses the three train/promote/fail tests.

Unit and integration counts will drop sharply; the build evidence must list the deleted and added counts per file so the drop is explained. `tests/unit/agent_packs/test_factory_packs.py` stays (retired persona ids).

## 6. Runbook (live test on Jarvis, after build)

Scratch first (`powershell -ExecutionPolicy Bypass -File scratch\c505_run.ps1 -Data c497_live -Wipe -Tag c497l`, port 8767), then serve on 0.0.0.0:8000.

1. **Startup:** the scratch server log has no Factory orchestrator lines, and `GET /api/health` returns 200.
2. **Removed routes:** `GET /api/agent_training_factory/jobs`, `GET .../gaps`, `GET .../phases/instructions` and `POST /api/agents/autoreiv/gaps/<id>/train` all return 404.
3. **Redirects:** `GET /api/agent_training_factory/capabilities` without following redirects returns 308 with `Location: /api/tools_studio/capabilities`. Following it returns the same `total_tools` as the new URL. `POST .../scaffold/runbook` through the redirect still returns a runbook.
4. **Skill Studio (desktop, Ctrl+F5):** open an existing skill, Generate, Save. DevTools Network shows only `/api/skill_studio/*` and `/api/tools_studio/capabilities`. The saved skill reopens with its tools.
5. **Tools Studio:** the catalog loads with the CARD-511 Checked labels, and `launch_factory_training` is not in it.
6. **Stranded gap:** put a gap in `training` in the scratch DB (a script with `update_gap_status`), then restart. It shows in Agent Studio's backlog as pending; Open in Skill Studio, Ask Developer and Dismiss work.
7. **AutoReiv intake (needs the LLM on the Spark):** "Teach AutoReiv to read IPMI sensor temperatures." AutoReiv inspects itself, asks a question or two, and hands off to Developer with a brief; it never mentions the Factory. **Fallback without the LLM:** `GET /api/agents/autoreiv` lists `inspect_agent_pack` and not `launch_factory_training`, and `GET /api/skill_studio/skills/agent-authoring` shows the new body.
8. **Teach regression:** Teach on a chat turn that needs a tool still shows Ask Developer (CARD-472).
9. **Busy check:** with a Studio job queued, `GET /api/system/updates/auto-status` reports busy with "running Studio job" and never "Factory".
10. **Phone** (`http://192.168.1.99:8000` after serve restart): repeat 4 and 5.
11. **Serve (Jacob's data):** after `scripts\restart_serve.ps1 -HostAddr 0.0.0.0 -Port 8000`, health returns 200 on 127.0.0.1 and 192.168.1.99. `%LOCALAPPDATA%\AutoReiv\packs\autoreiv\pack.json` and `skills\agent-authoring\SKILL.md` no longer mention `launch_factory_training` (startup refresh; the pack is not `user_modified`). `skills\build-agent-pack\SKILL.md` has no Factory lines if it was unedited. The `factory_*` tables still exist with 0 rows.

## 7. Definition of done

- REQ-497-001..015 pass; tests were written first and seen failing.
- Full suites pass apart from the known CARD-454/456 failures, with the count changes explained per file.
- The runbook passes on scratch and serve (desktop and phone).
- CARD-498's card notes the plain-SQL export and the maybe-missing `factory_phase_instructions`. CARD-512's card notes `self_scaffold_queue_e2e.py`. ADR-0060 carries the D6 location note.
- The card is set to In Review with evidence, then Done at `merge to qa`.

## What stays out of scope

- The remedy rename and Observability escalation fix (CARD-520).
- `/api/capabilities/scaffold/*`, `SelfScaffoldSpine`, `scaffold_spine` (CARD-512).
- Exporting and dropping the `factory_*` tables and columns, and removing the 308 redirects (CARD-498).
- Renaming Skill Studio's `factory*` element ids (ADR-0060 D5).
- A general fix for bundled seeds that never update (CARD-521).

---

## History: audit revisions (CARD-495 audit, 2026-09-25)

Kept for the record; the 2026-09-26 refinement above supersedes where they differ (D5 deletes `check_tool_collisions` instead of moving it; D6 moves `inspect_agent_pack` into `AgentPackTools`).

- **Depends on CARD-511.** Do not delete `verification_battery.py` / `tool_synthesizer.py` until CARD-511 has taken what it reuses (decision D6).
  - CARD-511 (refined 2026-09-26, its D2) keeps only `detect_path_safety_violation`, moved to `src/application/tools/tool_check.py` and re-exported from `verification_battery.py`. Once CARD-511 is merged, delete `verification_battery.py` **whole** (drop the re-export), plus `tool_synthesizer.py`. Nothing else uses them apart from the Factory, `jit_synthesizer.py` (built in `agent_kernel.py`, removed under D7), `hyperv_tool_builders.py` and their tests.
- **Keep `application/skills/workshop.py`** (Skill Studio persistence; used by `agents.py` L123/L247, `skill_authoring.py` L11, `skills.py` L172, `user_catalog.py` L406). Fix its docstring only.
- Move `llm.phase_llm_text` and `phases/promote.check_tool_collisions` with the scaffold routes.
- **Keep `inspect_agent_pack`**: move it into `orchestration_tools` and keep its grant in `pack.json` (decision D4). Delete only `launch_factory_training`.
- Also delete: `jit_synthesizer.py` and its construction in `agent_kernel.py` L136-138; `capability_graph.py`; `domain/orchestration/factory_packets.py`; `/train` and gap_link in `gaps.py` L117-176.
- Stop exposing `allow_autonomous_training` / `max_training_retries` in the API (`agents.py` L166, `registry.py` L157, `guardrails.py` L190, `skill_list.py`, `service.py`); keep the DB columns. Delete `KernelEventType.AUTO_TRAIN_PROGRESS` (`models.py` L185, `chat.py` L412-414) (decision D7).
- Drop the Factory checker from the busy detector (`busy.py` L122-134, `app.py` L357-358); Studio jobs stay counted.
