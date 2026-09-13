# [CARD-227] Observability Standing Journey Timeline

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Extend Observability studio + journey APIs for job_id-correlated standing path
> **Labels**: type:architecture, type:feature, AutoReiv.Observability, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **One Observability standing journey timeline** correlated by `job_id` — filter one job and see the full standing path (replay, not scattered panels).
2. **Includes**: Job/Phase steps, catalog matches, verifier statuses, CARD-221 policy decisions, A2A `child_job_id`, MCP BLOCKs, kill/resume.
3. **OpenTelemetry-style GenAI agent span tree / correlation** — one `job_id` filter yields the complete standing path.
4. **Proof**: API + Observability UI filter by `job_id` returns the complete journey including `resumed_from_checkpoint`.
5. **Not this card**: new Studios, merging session journey into Chat-only, inventing a second telemetry product, CARD-228+.

### Beat 2: What AutoReiv Does Now
1. Chat Journey Inspector (CARD-135) is **session**-scoped (`/api/chat/sessions/{id}/journey`) — jobs/phases/tools/facts, but not standing correlation by `job_id`.
2. Observability has KPI, logs, catalog match panel, tool-policy-decisions (session/agent), job-phase-memory (CARD-226) — **separate panels**, no single replay timeline.
3. A2A parent/child links are largely in-memory (`_a2a_child_links`); tool policy rows lack `job_id`; resume is proven in orchestrator but not replayed as a standing journey event.

### Beat 3: What Will Change
1. Add `GET /api/observability/standing-journey?job_id=` assembling one correlated timeline + span tree from Job/Phase, checkpoints (catalog + verifier), policy decisions (incl. MCP BLOCK), durable A2A child links, and resume events.
2. Observability UI: job_id filter + standing journey timeline (replay), reusing existing studio — not a new Studio.
3. Stamp `job_id` on policy decision log; persist A2A parent→child links; record `resumed_from_checkpoint` journey events on crash-resume.
4. TDD red→green; scorecard + CHANGELOG; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-SJURN-001]**: One Observability standing journey timeline correlated by `job_id` (filter one job → full standing path).
- [x] **[REQ-SJURN-002]**: Timeline includes Job/Phase steps, catalog matches, verifier statuses, CARD-221 policy decisions, A2A `child_job_id`, MCP BLOCKs, kill/resume.
- [x] **[REQ-SJURN-003]**: OpenTelemetry-style GenAI agent span tree / correlation keyed by `job_id` (not scattered panels without replay).
- [x] **[REQ-SJURN-004]**: Proof — API + Observability UI filter `job_id` returns complete journey including `resumed_from_checkpoint`.
- [x] **[REQ-SJURN-005]**: Extends existing Observability studio + journey APIs — no parallel product / theatre.
- [x] **[REQ-SJURN-006]**: Automated tests red→green; ruff clean; CHANGELOG + scorecard; push `feat/*` only — never qa/main. Live proof on Jarvis → Done when holds.

---

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: real durable correlation + API/UI replay proof.
- Out of scope: new Studios, replacing Chat session journey wholesale.

## 4. Modules Likely Touched

- `src/application/observability/standing_journey.py` (assembler)
- `src/web/routers/observability.py` + Observability UI (`observability.js`, `index.html`)
- `src/infrastructure/memory/schema.py` + repos (policy `job_id`, A2A links, journey events, list checkpoints)
- `src/application/orchestration/standing_a2a_handoff.py` / `job_phase_orchestrator.py` / `tool_policy_gate.py` / kernel gate
- `tests/unit/observability/test_standing_journey_timeline.py`
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- TDD: red "filter job_id → complete standing journey incl. resumed_from_checkpoint" first, then green.
- Extend Observability + standing path stores — do not invent a second timeline product.

## 6. Marathon Build Notes (Jarvis 2026-09-10 ET)

- `build_standing_journey(store, job_id=)` assembles one correlated timeline + OTel-style GenAI agent span tree.
- `GET /api/observability/standing-journey?job_id=` + Observability UI filter (`standingJourneyJobIdInput` / timeline).
- Durable `job_a2a_links`, `standing_journey_events` (resume), policy decisions stamp `job_id`; MCP BLOCKs included.
- Tests: `tests/unit/observability/test_standing_journey_timeline.py` (3) green; related suites green.
- Live smoke PASS: `notes/marathon-card227-live-smoke.json` (kinds + resumed_from_checkpoint + UI contract).
- Status: **Done** (unit + live assembler/UI proof; restart serve for live API on tip).
