# [CARD-319] Education Learning OS — Retention (Routine → Job from ledger next_due)

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-retention-319` (off `qa` @ 8d66d03)
> **Depends**: CARD-242 retention_routine; CARD-316/318 ledger next_due + binary grade
> **Labels**: type:feature, P0, Education, LearningOS, Retention, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. After a quiz miss sets `next_due`, review must come back automatically — not only when he opens Education.
2. Due items must mint a real **standing Job** (same job-graph as Chat), driven by a **Routine**, not a toast or side cron theatre.
3. Pause the Routine → no fire; resume → next due fires. After restart the schedule still matches the ledger.
4. No new Education chrome.

### Beat 2: What AutoReiv Does Now
1. CARD-242: `education-retrieval-retention` Routine id + `run_education_retention` + `POST /api/education/retention/run` mint standing Jobs for due mastery rows and set `pending_job_id`.
2. CARD-316/318: miss writes `next_due` on 1-3-7-30; Priming/Retrieval seed and grade the same ledger.
3. Gaps to prove/harden: enabled Routine gate (pause → no mint); resume → mint; restart-safe schedule vs ledger; miss on resurfaced practice advances the **same** mastery row; live smoke.

### Beat 3: What Will Change
1. Prove-and-harden Retention: ledger `next_due` drives Routine → standing Job; pause/resume behavior; same-row miss advance after resurface.
2. Name Routine id `education-retrieval-retention` + Job mint path in proof. Extend 242 primitives — no second scheduler.
3. TDD + live smoke. No new Studio panels.

## 2. Acceptance (Architect + Research locked)

- [ ] **[REQ-EDU-RSV-001]**: Due mastery rows (`next_due` ≤ now, no pending_job_id) mint standing Job(s) via Routine `education-retrieval-retention` / `run_education_retention` (same job-graph as Chat).
- [ ] **[REQ-EDU-RSV-002]**: Routine **disabled / paused** → no Job mint on tick or retention/run with gate; **enabled / resumed** → next due fires.
- [ ] **[REQ-EDU-RSV-003]**: Resurfaced practice miss updates the **same** mastery row (`next_due` advances on 1-3-7-30).
- [ ] **[REQ-EDU-RSV-004]**: After restart, due list + Routine schedule still match the ledger (`next_due` / pending_job_id).
- [ ] **[REQ-EDU-RSV-005]**: Proof: failing test → green; live smoke on Jarvis. No toast-only Done.
- [ ] **No new Education chrome** (UX lock).

## 3. Constraints

- Branch `feat/education-retention-319` off `qa` only. Never merge `main` unless Jacob asks. Hold FF→`qa` until **merge to qa**.
- Extend CARD-242 `retention_routine.py` + `/api/education/retention/run` — do not invent a parallel cron.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Jacob said **merge to qa and continue** — scaffold then **build** this card without a second build phrase.

## 4. Out of scope

- Amplifiers / Lumina / new Due chrome
- Adaptive SRS beyond 1-3-7-30
- Capability-gap smoke (follow-on after this wave)

## 5. Wave order

1. CARD-317/318 — Done on qa  
2. **This card** — Retention Routine→Job  
3. Capability-gap smoke → horizon triage

## 6. Reply phrases

- After In Review live OK → Jacob: **merge to qa**
