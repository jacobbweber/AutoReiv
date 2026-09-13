# [CARD-234] Supervisor Specialist Pick (Matched Catalog Only)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect feed after CARD-233; standing Job/Phase (215-233) + A2A never-widen (224) + mid-job scaffold park (233)
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AutoReiv.A2A, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. When a phase needs a specialist, `JobPhaseOrchestrator` picks the handoff target **only from matched catalog IDs** (agents/packs in the working set) — not free-form role theatre.
2. Handoff obeys **224 never-widen**: child inherits or strict-narrows matched subset + 221 decisions; linked `child_job_id` + checkpoint.
3. No match for needed specialty ⇒ park/scaffold (233) or fail-closed — never invent an out-of-catalog agent.
4. Observability journey shows `supervisor_pick` + child `job_id`; Chat strip shows parent↔child.
5. Closes wave 2 (230–234).

### Beat 2: What AutoReiv Does Now
1. CARD-224: A2A handoff inherits standing path, never-widen, linked child_job_id.
2. CARD-233: mid_job_self_scaffold park/scaffold on capability gap.
3. HandoffIsolationEngine + standing_a2a_handoff exist; no supervisor pick gated to matched catalog agent/pack IDs.
4. Chat strip shows Job/Phase/agent/react — no parent↔child link yet.

### Beat 3: What Will Change
1. Supervisor pick API on JobPhaseOrchestrator: specialty → matched agent/pack IDs only.
2. Out-of-catalog / free-form handoff rejected; no match → park or scaffold (233) or fail-closed.
3. Successful pick → create_standing_child_job (224) with never-widen + journey `supervisor_pick`.
4. Chat strip + journey surface parent↔child / supervisor_pick.
5. TDD red→green + live smoke; CHANGELOG + scorecard; push feat/* only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-SUPER-001]**: When a phase needs a specialist, `JobPhaseOrchestrator` picks handoff target **only from matched catalog IDs** (agents/packs in the working set) — not free-form role theatre.
- [x] **[REQ-SUPER-002]**: Handoff obeys **224 never-widen**: child inherits or strict-narrows matched subset + 221 decisions; linked `child_job_id` + checkpoint.
- [x] **[REQ-SUPER-003]**: No match for needed specialty ⇒ park/scaffold (233) or fail-closed — never invent an out-of-catalog agent.
- [x] **[REQ-SUPER-004]**: Observability journey shows `supervisor_pick` + child `job_id`; Chat strip shows parent↔child.
- [x] **[REQ-SUPER-005]**: Extends 215–233 + 224; red→green (incl. "out-of-catalog handoff rejected"); live smoke; feat-only.

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: real matched-catalog pick + 224 child link — not role-theatre crew invent.
- Out of scope: inventing new agents at pick time; qa/main push.
- Never invent out-of-catalog agents.

## 4. Modules Likely Touched

- `src/application/orchestration/supervisor_specialist_pick.py` (new)
- `src/application/orchestration/job_phase_orchestrator.py` (thin hook)
- `src/application/orchestration/standing_a2a_handoff.py` (reuse)
- `src/application/observability/standing_journey.py` (supervisor_pick span)
- `src/web/static/modules/studios/chat.js` + index.html (parent↔child strip)
- `tests/unit/orchestration/test_supervisor_specialist_pick.py` (new)
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- Architect Done bar locked — Builder implements now.
- TDD: red tests for 001–004 first (incl. out-of-catalog rejected), then green.
- Extend standing path + 224 handoff only — do not invent a second crew product.

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- `supervisor_specialist_pick.py`: pick only from matched `agent.*` / `pack.*` IDs; out-of-catalog rejected; no match => park/scaffold/fail_closed (never invent).
- Successful pick => CARD-224 `create_standing_child_job` (never-widen + linked `child_job_id` + checkpoint).
- Journey span `standing.supervisor_pick`; Chat strip `data-job-phase="link"` parent↔child.
- Thin orch hook: `JobPhaseOrchestrator.supervisor_pick_specialist`.
- Tests: `tests/unit/orchestration/test_supervisor_specialist_pick.py` (8) green; related suites green.
- Live smoke: `notes/marathon-card234-live-smoke.json`.
- Status: **Done**; closes wave 2 (230–234). Push `feat/*` only. Never invent out-of-catalog agents.
