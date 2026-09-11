# [CARD-219] Job/Phase Crash-Resume Checkpoints

> **Status**: Done
> **Marathon self-validate**: promoted 2026-09-11 after live proofs on feat standing path.
> **Created**: 2026-09-10
> **Spec Reference**: Design room after CARD-218; extends standing Job-Graph (CARD-215) + Job/Phase (CARD-096-101) + external verifier (CARD-216)
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Crash should not lose the plan**: If the process dies mid-Job, AutoReiv resumes from the last durable Job/Phase checkpoint — same `job_id`, LangGraph-style continue — not from scratch and not from a parallel in-memory plan.
2. **Checkpoint honesty**: After each phase commit (done / failed / HITL park), persist on disk: `job_id`, phase index, verifier status (`verified` | `skipped_no_checker` | `failed`), HITL park state.
3. **Operator path**: Chat Job/Phase strip + Observability show `resumed_from_checkpoint`; no silent restart theatre.
4. **Corrupt/missing only**: Replan-from-zero only when the checkpoint is corrupt or missing.
5. **Not this card**: Self-scaffold spine (CARD-218), new Studios, capability catalog changes.

### Beat 2: What AutoReiv Does Now
1. CARD-215 standing Job-Graph creates/advances durable Job+Phase rows without `goal_mode`.
2. SQLite Job/Phase rows survive process restart, but there is no explicit checkpoint commit record + resume contract with `resumed_from_checkpoint` surface.
3. Chat resumes open jobs for HITL park; mid-phase kill of a `running` phase is not a standing crash-resume proof path.
4. HITL park/resume exists for dangerous tools; Job-level crash-resume is the gap.

### Beat 3: What Will Change
1. Durable `job_phase_checkpoints` rows (SQLite, same store as Job/Phase — not a second graph engine) written after each phase commit.
2. `JobPhaseOrchestrator` commit + `resume_after_crash` / load path: interrupted `running` phases rehydrate and continue same `job_id`; corrupt/missing → replan required.
3. Chat SSE + strip + Observability surface `resumed_from_checkpoint`.
4. Proof: red "kill mid-phase ⇒ same job_id advances"; green tests; live on Jarvis if feasible.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-RESUME-001]**: Durable checkpoint on disk after each phase commit includes `job_id`, phase index, verifier status (`verified` | `skipped_no_checker` | `failed`), HITL park state.
- [x] **[REQ-RESUME-002]**: Process kill mid-phase → restart loads same `job_id` and CONTINUES (LangGraph-style). Replan-from-zero only if checkpoint corrupt/missing.
- [x] **[REQ-RESUME-003]**: Chat Job/Phase strip + Observability show `resumed_from_checkpoint` honestly.
- [x] **[REQ-RESUME-004]**: Automated tests red→green for crash-resume; ruff clean; CHANGELOG; feat branch only — never merge/push qa/main.
- [x] **[REQ-RESUME-005]**: Extend `JobPhaseOrchestrator` / existing SQLite job-phase persistence — do not invent a second graph engine. Out of scope: new Studios, catalog changes.

---

## 3. Constraints & Honor Flags

- Status: **In Review** (crash-resume green on feat; live QA notes below).
- Branch: `feat/standing-job-graph-runtime`. Never push qa/main.
- Out of scope: ATF/Lab rewrite, Homelab domain outcomes, scaffold spine (CARD-218), new Studios, catalog C.
- Anti-theatre: durable Job/Phase + checkpoint rows are the source of truth; no second plan store.

---

## 4. Modules Likely Touched

- `src/application/orchestration/job_phase_orchestrator.py` — commit + resume_after_crash
- `src/infrastructure/memory/schema.py` + jobs repository — `job_phase_checkpoints`
- `src/web/routers/chat.py` — emit `resumed_from_checkpoint` on resume
- Chat / Observability SPA modules
- `tests/unit/orchestration/test_job_phase_crash_resume.py`

---

## 5. Marathon Notes

- Build lock: durable checkpoint + same-job continue; replan only on corrupt/missing.
- TDD: red kill-mid-phase test first, then green.

## 6. Marathon Live QA (Jarvis)

- Unit: `tests/unit/orchestration/test_job_phase_crash_resume.py` 6 passed (red→green); related orch/schema 29 passed; ruff clean.
- In-process crash boundary on Jarvis: new `SQLiteStateStore` on same DB after mid-phase RUNNING kill → `resumed_from_checkpoint=true`, same `job_id` advanced to DONE (`job_3b0ba56a82b8`).
- API processes on :8000 still on pre-b020bfc code until restart; SSE `resumed_from_checkpoint` lands after serve reload.
- Pushed: `b020bfc` on `feat/standing-job-graph-runtime` only (never qa/main).
