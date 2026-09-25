---
id: CARD-497
title: "Retire the Agent Training Factory (3/4): move Studio routes, delete the training loop backend, update packs"
status: Ready
created: 2026-09-25
branch: qa
related:
  - CARD-495
  - CARD-496
  - CARD-498
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

> **Status**: Ready (after CARD-496)
> **Created**: 2026-09-25
> **Series**: CARD-495 → CARD-496 → **CARD-497** → CARD-498
> **Labels**: `type:cleanup`, `area:factory`, `area:backend`, `P1`

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine. No product code |
| **`build`** | Build test-first |
| **`merge to qa`** | After In Review and the runbook passes on Jarvis |

---

## 1. Four Beats

**Beat 1: What Jacob means.** The server no longer runs or exposes a training factory. The parts the Studios still use keep working under Studio names.

**Beat 2: What AutoReiv does now.** `src/web/routers/agent_training_factory.py` (prefix `/api/agent_training_factory`) mixes two groups.
- **Still used by the Studios:**
  - `GET /capabilities` (Skill Studio L389, Tools Studio catalog L513);
  - `POST /scaffold/runbook` and `/scaffold/save` (Skill Studio, `skill_authoring.js` `SILENT_RUNBOOK_URL`);
  - `GET /skills` and `/skills/{id}` (`workshop_meta.js`, `skill_scope.js`).
  - These rely on `agent_training_factory/llm.py` `phase_llm_text` (router L953) and `phases/promote.check_tool_collisions` (L16).
- **Training loop only:**
  - `/jobs*` (L237-439), `/gaps` (L357) and `/phases/*` (L796-815);
  - `POST /api/agents/{id}/gaps/{gap}/train` (`routers/gaps.py` L117; no UI caller);
  - the `FactoryOrchestrator` created at `app.py` L341 and started at L378 (polls every 2 s);
  - about 5,500 lines in `src/application/agent_training_factory/`, plus `orchestration/tool_synthesizer` and `capability_graph` users.
- **Chat tools:** `application/skills/factory_dispatch_tools.py` (`launch_factory_training`, `inspect_agent_pack`) is granted by `platform-packs/autoreiv/pack.json` L89-97 and L164-165, and the `agent-authoring` skill (SKILL.md L7-8, L51) tells AutoReiv to launch training jobs.
- **Remedy type:** `factory_escalation` appears in `domain/observability/models.py` L95, `tool_skill_resolver.py` L215, `observability.js` L835, and the distill output (`skills/distillation_service.py` L245-315).

**Beat 3: What will change.**
1. **Move** `/capabilities`, `/scaffold/runbook`, `/scaffold/save`, `/skills` and `/skills/{id:path}` to a new `routers/skill_studio.py` under `/api/skill_studio/*` and `/api/tools_studio/capabilities`.
   - Update the frontend callers in the same branch.
   - Keep the old paths as thin 308 redirects for one release (removed in CARD-498).
   - Move `phase_llm_text` and `check_tool_collisions` to `application/skills/`.
2. **Delete:**
   - `/jobs*`, `/gaps`, `/phases/*` and the gap `/train` endpoint;
   - `FactoryOrchestrator` startup and shutdown;
   - `application/agent_training_factory/` (after the moves), `factory_dispatch_tools.py`, `FactoryPacketRepository` writers, and the `prompt_registry` table creator;
   - unused `orchestration` helpers, checked with `rg`.
3. **Packs:**
   - drop `launch_factory_training` and `inspect_agent_pack` from `autoreiv`;
   - rewrite `agent-authoring` to hand off to the Developer (`handoff_to_agent` → `developer`) or retire it;
   - add both tool ids to the retired-tools list so persisted grants are purged (ADR-0056 reconciler).
4. **Rename** `factory_escalation` to `tool_escalation` in the distill output and the observability remedy kind. Readers accept the old name for existing rows and messages.

**Beat 4: What dies.** The autonomous training loop, its endpoints and background runner, and the chat tool that starts it.

## 2. Acceptance criteria (EARS)

- **[REQ-497-001]** WHEN the app starts, THE SYSTEM SHALL NOT create or start a `FactoryOrchestrator`.
- **[REQ-497-002]** Requests to `/api/agent_training_factory/jobs*`, `/gaps`, `/phases/*` and `/api/agents/{id}/gaps/{gap}/train` SHALL return 404.
- **[REQ-497-003]** Skill Studio and Tools Studio SHALL load capabilities, generate a runbook, save a skill and open existing skills through the new routes, with identical payloads.
- **[REQ-497-004]** THE SYSTEM SHALL NOT offer `launch_factory_training` or `inspect_agent_pack` to any agent, and existing grants SHALL be purged on reconcile.
- **[REQ-497-005]** Distill output and observability remedies SHALL use `tool_escalation`, and SHALL still read stored `factory_escalation` values.

## 3. Decisions

| # | Decision | Recommendation |
|---|----------|----------------|
| D1 | Route aliases | **308 redirects for one release**, then delete in CARD-498 |
| D2 | `agent-authoring` skill | **Rewrite as a Developer handoff** (Socratic intake stays useful) |
| D3 | Remedy rename | **`tool_escalation`**, reading the old name as well |

## 4. Failing-tests-first plan

- **pytest:**
  - the new route tests (copy the payload assertions from `test_scaffolder_endpoints.py`, `test_card_418_skill_studio_save.py`, `test_workshop_skill_resolve.py`);
  - negative 404 tests for the removed routes;
  - app startup has no `factory_orchestrator` on `app.state`;
  - pack reconcile purges the two tools;
  - distill returns `tool_escalation`;
  - observability reads both names.
- Delete the Factory-only tests (ADR-0055): `tests/unit/agent_training_factory/*` except the scaffold/skills ones that move, `test_factory_api`, `test_factory_runner`, `test_factory_packets`, `test_factory_dispatch_tools`, `test_capability_loop`, `integration/factory/test_dogfood_factory_pipeline`, and `integration/capabilities/test_dogfood_capability_gap_loop` (rewrite it as gap → backlog only).
- **Vitest:** Skill Studio and Tools Studio call the new URLs.
- **Smoke:** Skill Studio generate and save on the scratch server.

## 5. Runbook

On the scratch server:
1. Skill Studio: open a skill, Generate, Save.
2. Tools Studio: the catalog loads.
3. `curl` `/api/agent_training_factory/jobs` returns 404.
4. Serve logs show no factory polling.
