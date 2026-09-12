# AutoReiv Design Marathon Scorecard - Standing Job/Phase Runtime

**Branch**: `feat/standing-job-graph-runtime`  
**Jarvis date**: 2026-09-11 ET (UTC-4)  
**Serve**: `http://127.0.0.1:8000` @ package `0.28.0` + tip (CARD-234) - Ollama `qwen3.8:latest` @ `192.168.1.29:11434`  
**Standing budget**: `STANDING_PHASE_LLM_TIMEOUT_SECONDS=1800`







## CARD-255 - Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-SSQ-001]** Full path candidate -> sandbox -> HITL -> trusted (218 + 233 + 251)
- **[REQ-SSQ-002]** Rollback restores prior trusted snapshot
- **[REQ-SSQ-003]** Standing Job resolve trusted-only; no auto-trust of candidates
- **[REQ-SSQ-004]** Education gap Ask -> Forge -> Approve -> next Job uses trusted skill
- **[REQ-SSQ-005]** Tests + live smoke + CHANGELOG; feat-only; do not invent 257

Tests: `tests/unit/orchestration/test_self_scaffold_queue_e2e_255.py` (6) + 218/233/251/catalog green.

Live smoke PASS: `notes/marathon-card255-live-smoke.json`.

Wave tip stack (CoS): **256 -> 251 -> 252 -> 253 -> 254 -> 255** (this tip).


## CARD-254 - Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-VRH-001]** Binary external verify only; LLM self-critique never standing verified
- **[REQ-VRH-002]** Forced fail -> replan <=3 -> HITL park (232 class); no infinite loop
- **[REQ-VRH-003]** Handoff != replan (child create does not bump replan_count)
- **[REQ-VRH-004]** Chat standing checker-fail uses phase-complete gate (not fail_phase)
- **[REQ-VRH-005]** Tests + live smoke + CHANGELOG; feat-only; do not start 255

Tests: `tests/unit/orchestration/test_verifier_replan_harden_254.py` (6) + 216/232 suites green.

Live smoke PASS: `notes/marathon-card254-live-smoke.json` (forced fail -> replan x3 -> park).


## CARD-253 - Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-LRCTX-001]** Phase-scoped working set holds N→N+1 under qwen (no dump-all theatre)
- **[REQ-LRCTX-002]** Multi-phase Job kill/resume; N+1 sees ledger/memory facts
- **[REQ-LRCTX-003]** Full transcript dump must not masquerade as memory (fail closed)
- **[REQ-LRCTX-004]** Extends 228/229 (+226); AGENTS.md tools still on Chat
- **[REQ-LRCTX-005]** Tests + live smoke + CHANGELOG; feat-only; do not start 254

Tests: `tests/unit/orchestration/test_long_run_context_253.py` (5) + 226/229 suites green.

Live smoke PASS: `notes/marathon-card253-live-smoke.json` (kill/resume + qwen2.5:3b SAW_LEDGER=yes).


## Cards 215-229

| Card | Status | One-line capability |
|------|--------|---------------------|
| **CARD-215** | Done | Standing Job/Phase runtime replaces goal_mode theatre for multi-step Chat. |
| **CARD-216** | Done | External verifier policy with honest `verified` / `skipped_no_checker` / `failed`. |
| **CARD-217** | Done | Match-only capability catalog C (intent to matched IDs, no silent invent). |
| **CARD-218** | Done | Self-scaffold spine candidate to trusted + Forge queue. |
| **CARD-219** | Done | Job/Phase crash-resume checkpoints (same `job_id`, no cold replan when checkpoint ok). |
| **CARD-220** | Done | Catalog resolve into JobPhaseOrchestrator + Chat standing multi-step entry. |
| **CARD-221** | Done | Tool policy gate ALLOW / REQUIRE_CONFIRM / BLOCK before executor. |
| **CARD-222** | Done | Routines join standing Job/Phase path (cron=trigger only; durable `job_id`). |
| **CARD-223** | Done | Steering truth sync: roadmap M15-17, product.md, OpenAPI to 0.28.0. |
| **CARD-224** | Done | A2A handoff inherits standing path (linked `child_job_id`, no tool widen). |
| **CARD-225** | Done | MCP tools through matched-subset + CARD-221 gate (tools/list is not auth). |
| **CARD-226** | Done | Job/Phase cross-phase memory.db recall (never storage.db; kill/resume proof). |
| **CARD-227** | Done | Observability standing journey timeline correlated by job_id (replay + span tree). |
| **CARD-228** | Done | Progressive SKILL.md disclosure (resolve metadata-only; bind loads one body; tools still on Chat). |

## CARD-229 (this turn) - PASS to Done

Locked Done bar:
- Each Job/Phase turn carries working set: phase goal + matched metadata + **bound** skill body only + this-phase memory.db facts
- Prior phases → short durable notes (not raw tool dumps / unbound skill bodies)
- Proof: phase N+1 prompt excludes unbound skill bodies and prior-phase tool dumps
- Align with existing compaction (M12 / CARD-041 ContextCompactor); wire Chat + Routines standing path
- Keep AGENTS.md: ticked tools still listed every Chat turn

Tests: `tests/unit/orchestration/test_phase_scoped_working_set.py` (5) + related memory/skill/compaction green.

Live smoke PASS: `notes/marathon-card229-live-smoke.json`.

## CARD-228 (prior) - PASS to Done


Locked Done bar:
- Catalog/resolve returns skill **metadata only**: id, title, risk, HITL flags — NO full SKILL.md body
- Full runbook body loads only when a phase **binds/selects** that skill
- Dump-all skill bodies at resolve is forbidden (qwen context tax / theatre)
- **CRITICAL AGENTS.md invariant**: Chat still lists that agent's **ticked tools** every turn
- Proof: resolve payload has no skill body; bind event loads one body; tool schemas still present on Chat turn

Tests: `tests/unit/capabilities/test_progressive_skill_disclosure.py` (6) + related catalog suites green.

Live smoke PASS: `notes/marathon-card228-live-smoke.json`.

## CARD-227 (prior) - PASS to Done

Locked Done bar:
- One Observability standing journey timeline correlated by `job_id`
- Includes Job/Phase, catalog matches, verifier, 221 policy, A2A child_job_id, MCP BLOCKs, kill/resume
- OpenTelemetry-style GenAI agent span tree — filter one job_id → full standing path
- Not scattered panels without replay
- Proof: API + UI filter job_id returns complete journey including `resumed_from_checkpoint`

Tests: `tests/unit/observability/test_standing_journey_timeline.py` (3) + related crash-resume/policy/journey green.

Live smoke PASS: `notes/marathon-card227-live-smoke.json`.

## CARD-226 (prior) - PASS to Done

Locked Done bar:
- Recall from `<agent>_memory.db` only — NEVER `<agent>_storage.db`
- Phase reflections/facts persist on job checkpoint path and/or memory.db
- Proof: phase N writes a fact; kill/resume; phase N+1 recalls that fact
- Align with CARD-116 assembler/repo; standing Job/Phase path uses it
- Studio/Observability: `memory_recalled` SSE + `/api/observability/job-phase-memory`

Tests: `tests/unit/orchestration/test_job_phase_cross_phase_memory.py` (5) + related crash-resume/memory/routines green.

Live smoke PASS: `notes/marathon-card226-live-smoke.json` (write→kill/resume→recall; storage.db absent).

## CARD-225 (prior) - PASS to Done

Locked Done bar:
- MCP = transport only; tools/list is not authorization
- Mounted MCP tools hit matched capability subset + ToolPolicyGate ALLOW/REQUIRE_CONFIRM/BLOCK
- Outside-subset / unknown MCP to BLOCK (never reaches executor)
- Dangerous MCP to REQUIRE_CONFIRM to existing HITL
- Proof: red "listed MCP tool outside matched IDs never runs" to green
- Extends MCPClientAdapter / ScopedToolRegistry / ToolPolicyGate — no parallel auth

Tests: `tests/unit/safety/test_mcp_tool_policy_gate.py` + prior CARD-221 suites green.

Live smoke PASS: `notes/marathon-card225-live-smoke.json` (outside-subset BLOCK + dangerous REQUIRE_CONFIRM + safe ALLOW). Observability tool-policy-decisions API still 200 on serve. Full Chat+mounted-MCP E2E optional (no dedicated MCP server required for Done bar unit/live gate proof).

## CARD-222 live E2E (prior) - PASS to Done

Artifact: `notes/marathon-card222-e2e-2026-09-10.json`

## CARD-224 live smoke (prior) - PASS

Artifact: `notes/marathon-card224-live-smoke.json`

## Wave 2 (230–234) — Done

| Card | Status | One-line capability |
|------|--------|---------------------|
| **CARD-230** | Done | Outcome intake: outcome-shaped Chat ask → durable Job + testable `success_rule` + matched IDs; vibes reject; fail-closed before phase 1. |
| **CARD-231** | Done | Standing research-before-plan on capability gap only. |
| **CARD-232** | Done | Bounded auto-replan (N=3) then HITL park. |
| **CARD-233** | Done | Mid-job self-scaffold via 218 spine (candidate only). |
| **CARD-234** | Done | Supervisor specialist pick from matched catalog (224 never-widen). |

## CARD-230 — Done (unit green; live smoke see artifact)

Locked Done bar:
- **[REQ-INTAKE-001]** Outcome-shaped Chat ask → durable Job; no goal_mode; short turns stay ReAct
- **[REQ-INTAKE-002]** Persist testable `success_rule`; vibes-only reject at intake
- **[REQ-INTAKE-003]** Catalog resolve at intake; matched IDs authority; agent picker preference only
- **[REQ-INTAKE-004]** Fail-closed before phase 1 if missing `success_rule` or `matched_capability_ids`
- **[REQ-INTAKE-005]** Extends 215–229 only
- **[REQ-INTAKE-006]** Red→green unit tests; CHANGELOG + scorecard; feat-only

Tests: `tests/unit/orchestration/test_outcome_intake.py` (10) + related standing/catalog suites green.

Live smoke PASS: `notes/marathon-card230-live-smoke.json` (intake Job has testable success_rule + matched IDs; phase 1 start ok; vibes reject; serve health ok; Ollama qwen3.8:latest present).

## CARD-231 — Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-RESEARCH-001]** Thin/gap → Research before Formulate/Execute
- **[REQ-RESEARCH-002]** Sufficient → skip research (Formulate/Execute only)
- **[REQ-RESEARCH-003]** Research writes memory.db + catalog-gap proposals; no trusted skill/tool writes
- **[REQ-RESEARCH-004]** Checkpoint `research_inserted` + reason; journey `standing.research` span
- **[REQ-RESEARCH-005]** Extends 215–230; red→green; feat-only

Heuristic: empty matched IDs | count < 2 | missing critical roles (health/verify/wiki/execute) implied by success_rule.

Tests: `tests/unit/orchestration/test_research_before_plan.py` (9) + related standing/catalog suites green.

Live smoke PASS: `notes/marathon-card231-live-smoke.json`.


## CARD-232 - Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-REPLAN-001]** On verifier `failed`, Job replans remaining phases against same `success_rule` + matched IDs - never silent advance
- **[REQ-REPLAN-002]** Cap N=3; 4th fail => HITL park with reason
- **[REQ-REPLAN-003]** `skipped_no_checker` still != verified advance; only `failed` triggers replan
- **[REQ-REPLAN-004]** Checkpoint `replan_count` + last fail reason; journey replan + park spans
- **[REQ-REPLAN-005]** Extends 215-231; red->green; live smoke; feat-only

Tests: `tests/unit/orchestration/test_bounded_auto_replan.py` (7) + related standing/catalog/crash-resume/journey green.

Live smoke PASS: `notes/marathon-card232-live-smoke.json`.

## CARD-233 - Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-SCAFFOLD-001]** Gap on running Job → candidate via 218 spine (never trusted from live phase)
- **[REQ-SCAFFOLD-002]** draft → sandbox → version → HITL → trusted → catalog re-resolve (matched IDs); reject unscoped trusted write
- **[REQ-SCAFFOLD-003]** Park or continue-matched-only until promote; no silent candidate-as-trusted
- **[REQ-SCAFFOLD-004]** Journey `scaffold_candidate` + HITL + re-resolve spans; Forge candidate queue
- **[REQ-SCAFFOLD-005]** Extends 215–232 + 218; red→green; live smoke; feat-only

Tests: `tests/unit/orchestration/test_mid_job_self_scaffold.py` (9) + related standing/scaffold/journey green.

Live smoke PASS: `notes/marathon-card233-live-smoke.json`.

## CARD-234 - Done (unit green; live smoke PASS)

Locked Done bar:
- **[REQ-SUPER-001]** Pick handoff target only from matched catalog agent/pack IDs
- **[REQ-SUPER-002]** 224 never-widen + linked child_job_id + checkpoint
- **[REQ-SUPER-003]** No match => park/scaffold/fail-closed; out-of-catalog rejected (never invent)
- **[REQ-SUPER-004]** Journey `supervisor_pick` + child job_id; Chat strip parent↔child
- **[REQ-SUPER-005]** Extends 215–233 + 224; red→green; live smoke; feat-only

Tests: `tests/unit/orchestration/test_supervisor_specialist_pick.py` (8) + related standing/a2a/chat/journey green.

Live smoke PASS: `notes/marathon-card234-live-smoke.json`.

## Wave 2 closed

Cards 230–234 all Done on `feat/standing-job-graph-runtime`.

## Artifacts
- CARD-234 live smoke: `notes/marathon-card234-live-smoke.json`
- CARD-233 live smoke: `notes/marathon-card233-live-smoke.json`
- CARD-232 live smoke: `notes/marathon-card232-live-smoke.json`
- CARD-230 live smoke: `notes/marathon-card230-live-smoke.json`
- CARD-254 live smoke: `notes/marathon-card254-live-smoke.json`
- CARD-253 live smoke: `notes/marathon-card253-live-smoke.json`
- CARD-229 live smoke: `notes/marathon-card229-live-smoke.json`
- CARD-228 live smoke: `notes/marathon-card228-live-smoke.json`
- CARD-227 live smoke: `notes/marathon-card227-live-smoke.json`
- CARD-227 live API: `notes/marathon-card227-live-api.json`
- CARD-226 live smoke: `notes/marathon-card226-live-smoke.json`
- CARD-222 E2E: `notes/marathon-card222-e2e-2026-09-10.json`
- CARD-224 live smoke: `notes/marathon-card224-live-smoke.json`
- Prior smoke: `notes/marathon-live-smoke-2026-09-10.json`
- This scorecard: `notes/marathon-scorecard-standing-job-graph.md`



