# [CARD-253] Long-run context (228/229 class)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Phase-scoped working set holds across N→N+1 under qwen; no context theatre. Live: Multi-phase Job survives kill/resume; phase N+1 sees ledger/memory facts not full prior dump. Research: Copy working-set / progressive skill load; prove under qwen N→N+1 + kill/resume. Skip dumping full transcripts as memory.
> **Labels**: type:architecture, type:feature, P1, ControlPlane, Context, AntiTheatre, KillResume, Qwen
> **Branch**: `feat/long-run-context-253` (off `feat/frozen-eval-pack-252` @ 4b60af4)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Long-run Jobs** keep a **phase-scoped working set** across N→N+1 under **qwen** (228 progressive skill load + 229 working set) - not context theatre / dump-all.
2. **Kill/resume** of serve or process: multi-phase Job survives; phase N+1 rebuilds from **ledger / memory.db facts** + durable notes - **never** a full prior transcript dump masquerading as memory.
3. Proof: N writes fact → kill/resume → N+1 prompt has the fact; full transcript dump is rejected / fails the gate.
4. Mark CARD-252 Done. Do **not** start CARD-254.

### Beat 2: What AutoReiv Does Now
1. CARD-228 progressive SKILL.md (metadata resolve; one-body bind) and CARD-229 phase-scoped working set are Done for in-process N→N+1.
2. CARD-226 persists job-scoped facts to `*_memory.db` and crash-resume recalls lines - but persist still accepts up to 4000-char blobs, and there is **no explicit fail** when a full Chat transcript is stuffed into memory as a "fact".
3. Resume path rebuilds working set from memory facts + progressive bind, but live kill/resume under **qwen** + anti-transcript theatre is not locked as a 228/229-class marathon card.

### Beat 3: What Will Change
1. Harden memory write/recall + working-set rebuild: sanitize facts; **reject transcript dumps** masquerading as memory; distill prior to durable notes.
2. `rebuild_working_set_after_resume` (ledger/memory + progressive skill bind) for N+1 after kill/resume - never `get_session_transcript` as prior.
3. TDD red→green; live smoke multi-phase Job kill/resume under qwen → `notes/marathon-card253-live-smoke.json`. Mark 252 Done. Push feat only.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-LRCTX-001]**: Phase-scoped working set (goal + matched metadata + this-phase bound skill body + this-phase memory facts + prior durable notes) holds across N→N+1 under qwen - no dump-all / context theatre.
- [x] **[REQ-LRCTX-002]**: Multi-phase Job survives kill/resume (serve or process); phase N+1 sees ledger/memory facts needed for continuation.
- [x] **[REQ-LRCTX-003]**: Full prior transcript dump must **not** masquerade as memory - sanitize/reject; tests fail the dump path.
- [x] **[REQ-LRCTX-004]**: Extends CARD-228/229 (+226 recall) only - copy working-set / progressive skill load; no second context product; AGENTS.md tools still listed every Chat turn.
- [x] **[REQ-LRCTX-005]**: Automated tests red→green; live smoke `notes/marathon-card253-live-smoke.json`; CHANGELOG + scorecard; push `feat/*` only - never qa/main; do not start 254.

## 3. Constraints

- Branch `feat/long-run-context-253` off `feat/frozen-eval-pack-252` @ 4b60af4. Never qa/main. Do **not** merge to grok.
- Skip dumping full transcripts as memory. Prefer memory.db ledger facts + durable notes.
- Do not start CARD-254.

## 4. Out of scope

- CARD-254+
- Merging to grok / qa / main
- Replacing M12 ContextCompactor / inventing a second compaction engine
- Hiding Chat ticked tools behind skills

## 5. Proof

- Unit: working-set retention across phases + kill/resume rebuild; transcript-dump-as-memory fails.
- Live: multi-phase Job kill/resume; N+1 has facts not full dump → `notes/marathon-card253-live-smoke.json`.

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- Extended CARD-228/229 working-set + progressive bind with CARD-253 long-run guards.
- `looks_like_transcript_dump` / `sanitize_memory_fact` / `assert_not_transcript_memory` reject full Chat transcript dumps as memory.
- `JobPhaseMemoryBridge.persist_phase_facts` + `prior_lines_from_job_memory` sanitize (ledger facts only).
- `rebuild_working_set_after_resume` rebuilds N+1 from memory.db + progressive bind; `session_transcript` seed fails closed.
- Chat resume remaining-phases path uses rebuild when durable_notes empty after kill/resume.
- Tests: `tests/unit/orchestration/test_long_run_context_253.py` (5) + related 226/229 green.
- Live smoke PASS: `notes/marathon-card253-live-smoke.json` (kill/resume + qwen2.5:3b SAW_LEDGER=yes).
- Status: **Done**. Do not start CARD-254. Push `feat/*` only.
