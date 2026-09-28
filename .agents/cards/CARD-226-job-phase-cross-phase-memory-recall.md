# [CARD-226] Job/Phase Cross-Phase memory.db Recall

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Align standing Job/Phase path with CARD-116 Agent Brain
> **Labels**: 	ype:architecture, 	ype:feature, AutoReiv.Memory, AutoReiv.Orchestration, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Cross-phase recall must use <agent>_memory.db only** — never <agent>_storage.db (CARD-148 domain store stays separate).
2. **Phase reflections/facts persist on the job checkpoint path and/or memory.db** so kill/resume does not wipe prior-phase knowledge.
3. **Proof**: phase N writes a fact; kill/resume; phase N+1 recalls that fact from durable cognitive memory.
4. **Close theatre**: standing Job/Phase currently keeps prior/ccumulated in-process (empty on resume). Wire the existing CARD-116 assembler/repo into the standing path for real write+recall.
5. **Studio/Observability**: surface recalled facts or checkpoint memory refs where natural (SSE + Observability API).
6. **Not this card**: new Studios, merging memory into storage.db, inventing a second brain, CARD-227+.

### Beat 2: What AutoReiv Does Now
1. CARD-116 shipped AgentMemoryRepository + MemoryContextAssembler on <slug>_memory.db; AgentKernel injects shelves on plain turns.
2. Standing Job/Phase stores phase outputs on HandoffPacket / output_packet_json and passes ephemeral ccumulated / prior into phase_assignment_prompt — **resume path resets prior = []**.
3. JobPhaseCheckpoint (CARD-219/220) persists verifier + matched capability IDs but **not** memory fact refs; no job-scoped write into memory.db on phase complete.

### Beat 3: What Will Change
1. On phase complete: persist reflections/facts into the agent *_memory.db via existing repo (entity scoped to job:{job_id}), and stamp memory_fact_ids on the durable checkpoint.
2. On next phase / crash-resume: recall job-scoped facts from memory.db (assembler/repo) into prior context — never from storage.db.
3. Emit memory_recalled SSE + Observability endpoint for checkpoint memory refs / recalled facts.
4. TDD red->green proof; scorecard + CHANGELOG; push eat/* only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-JPMEM-001]**: Standing Job/Phase cognitive write+recall uses <agent>_memory.db only — never <agent>_storage.db.
- [x] **[REQ-JPMEM-002]**: Phase reflections/facts persist via memory.db and/or checkpoint memory_fact_ids on the job checkpoint path.
- [x] **[REQ-JPMEM-003]**: Proof — phase N writes a fact; process kill/resume; phase N+1 recalls that fact from durable memory.
- [x] **[REQ-JPMEM-004]**: Align with existing CARD-116 AgentMemoryRepository / MemoryContextAssembler — standing path uses them (close ephemeral-prior theatre).
- [x] **[REQ-JPMEM-005]**: Studio/Observability surfaces recalled facts or checkpoint memory refs (SSE and/or API).
- [x] **[REQ-JPMEM-006]**: Automated tests red->green; ruff clean; CHANGELOG + scorecard; push eat/* only — never qa/main. Live proof on Jarvis when feasible -> In Review or Done.

---

## 3. Constraints & Honor Flags

- Branch: eat/standing-job-graph-runtime. Never merge/push qa/main.
- Anti-theatre: real loop + durable state + test/live proof (no in-process-only prior).
- Out of scope: new Studios, storage.db blending, second memory engine.

## 4. Modules Likely Touched

- src/application/orchestration/job_phase_memory.py (new bridge)
- src/application/orchestration/job_phase_orchestrator.py / chat_job_binding.py / chat.py
- src/domain/orchestration/models.py (checkpoint memory refs)
- src/infrastructure/memory/schema.py + 
epositories/jobs.py + connection.py
- src/web/routers/observability.py
- 	ests/unit/orchestration/test_job_phase_cross_phase_memory.py
- 
otes/marathon-scorecard-standing-job-graph.md, CHANGELOG.md

## 5. Marathon Build Lock

- TDD: red "phase N write -> kill/resume -> phase N+1 recall from memory.db" first, then green.
- Extend CARD-116 brain — do not invent a parallel store or touch storage.db.

## 6. Marathon Build Notes (Jarvis 2026-09-10 ET)

- New `JobPhaseMemoryBridge` writes/recalls job-scoped facts via CARD-116 `AgentMemoryRepository` (`*_memory.db` only).
- `complete_phase` persists facts + stamps accumulating `memory_fact_ids` on `job_phase_checkpoints`.
- Standing Chat/Routines/resume rebuild `prior` from memory.db (closes empty-prior theatre).
- SSE `memory_recalled` + `GET /api/observability/job-phase-memory`.
- Tests: `tests/unit/orchestration/test_job_phase_cross_phase_memory.py` (5) green; related suites green.
- Live smoke PASS: `notes/marathon-card226-live-smoke.json`.
- Status: **Done** (unit + live kill/resume recall proof on Jarvis).
