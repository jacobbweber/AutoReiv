# AutoReiv Design Marathon Scorecard - Standing Job/Phase Runtime

**Branch**: `feat/standing-job-graph-runtime`  
**Jarvis date**: 2026-09-10 ET (UTC-4) / early 2026-09-11 UTC  
**Serve**: `http://127.0.0.1:8000` @ package `0.28.0` + tip (CARD-225) - Ollama `qwen3.8:latest` @ `192.168.1.29:11434`  
**Standing budget**: `STANDING_PHASE_LLM_TIMEOUT_SECONDS=1800`

## Cards 215-225

| Card | Status | One-line capability |
|------|--------|---------------------|
| **CARD-215** | Done | Standing Job/Phase runtime replaces goal_mode theatre for multi-step Chat. |
| **CARD-216** | Done | External verifier policy with honest `verified` / `skipped_no_checker` / `failed`. |
| **CARD-217** | In Review | Match-only capability catalog C (intent to matched IDs, no silent invent). |
| **CARD-218** | In Review | Self-scaffold spine candidate to trusted + Forge queue. |
| **CARD-219** | In Review | Job/Phase crash-resume checkpoints (same `job_id`, no cold replan when checkpoint ok). |
| **CARD-220** | Done | Catalog resolve into JobPhaseOrchestrator + Chat standing multi-step entry. |
| **CARD-221** | Done | Tool policy gate ALLOW / REQUIRE_CONFIRM / BLOCK before executor. |
| **CARD-222** | Done | Routines join standing Job/Phase path (cron=trigger only; durable `job_id`). |
| **CARD-223** | Done | Steering truth sync: roadmap M15-17, product.md, OpenAPI to 0.28.0. |
| **CARD-224** | Done | A2A handoff inherits standing path (linked `child_job_id`, no tool widen). |
| **CARD-225** | Done | MCP tools through matched-subset + CARD-221 gate (tools/list is not auth). |

## CARD-225 (this turn) - PASS to Done

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

## Do not start

- **CARD-226** not started this turn.

## Artifacts
- CARD-222 E2E: `notes/marathon-card222-e2e-2026-09-10.json`
- CARD-224 live smoke: `notes/marathon-card224-live-smoke.json`
- Prior smoke: `notes/marathon-live-smoke-2026-09-10.json`
- This scorecard: `notes/marathon-scorecard-standing-job-graph.md`


