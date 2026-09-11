# [CARD-219] Job/Phase Crash-Resume Checkpoints

> **Status**: Ready
> **Created**: 2026-09-10
> **Spec Reference**: Design room after CARD-218; extends standing Job-Graph (CARD-215) + Job/Phase (CARD-096-101)
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Crash should not lose the plan**: If the process dies mid-Job, AutoReiv resumes from the last durable Job/Phase checkpoint — not from scratch and not from a parallel in-memory plan.
2. **Checkpoint honesty**: Each phase transition (queued → running → done/failed/parked) is durable before side effects that matter; resume reloads that state.
3. **Operator path**: Chat Job/Phase strip + Observability show resume; no silent restart theatre.
4. **Not this card**: Self-scaffold write spine (CARD-218). Do not rebuild capability catalog here.

### Beat 2: What AutoReiv Does Now
1. CARD-215 standing Job-Graph creates/advances durable Job+Phase rows without `goal_mode`.
2. Process restart / crash recovery of in-flight phases is not a standing resume contract with explicit checkpoint + resume API/runbook.
3. HITL park/resume exists for dangerous tools; Job-level crash-resume is the gap.

### Beat 3: What Will Change (sketch only — Ready, do not build until locked)
1. Explicit checkpoint records (or hardened Job/Phase row invariants) at phase boundaries.
2. Boot/resume path: detect interrupted `running` phases → rehydrate orchestrator → continue or fail closed with operator-visible state.
3. Proof: red "resume after crash continues from last checkpoint"; then green. Live QA: kill process mid-phase, restart, confirm resume.

---

## 2. Acceptance Criteria (Definition of Done) — Ready sketch

- [ ] **[REQ-RESUME-001]**: Job/Phase checkpoint durable at phase boundary before continuing side effects.
- [ ] **[REQ-RESUME-002]**: After process crash/restart, orchestrator resumes interrupted Job from last checkpoint (or fails closed visibly).
- [ ] **[REQ-RESUME-003]**: Chat/Observability surface resumed vs fresh Job honestly.
- [ ] **[REQ-RESUME-004]**: Automated tests red→green for crash-resume; ruff clean; CHANGELOG; feat branch only — never merge qa/main.

---

## 3. Constraints & Honor Flags

- Status: **Ready**. Do not set In Progress or write product code until Jacob explicitly says **build**.
- Branch: continue feat cut from grok / standing-job-graph line. Never push qa/main.
- Out of scope until build: ATF/Lab rewrite, Homelab domain outcomes, scaffold spine changes (CARD-218).
- Anti-theatre: durable Job/Phase is the checkpoint; no second plan store.

---

## 4. Modules Likely Touched (inventory only)

- `src/application/orchestration/job_phase_orchestrator.py`
- Job/Phase schema + repositories
- Chat binding / Observability status strip
- `tests/unit/orchestration/` crash-resume cases

---

## 5. Marathon Notes

- Sketched Ready only after CARD-218 In Review. Do not deep-implement until build lock.
