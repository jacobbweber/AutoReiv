# [CARD-229] Phase-Scoped Working-Set Context

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Standing Job/Phase Chat/Routines path + M12 ContextCompactor alignment (CARD-041) + CARD-226 memory + CARD-228 progressive skills
> **Labels**: type:architecture, type:feature, AutoReiv.Orchestration, AutoReiv.Memory, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Each Job/Phase turn carries a working set**: phase goal + matched capability **metadata** + **bound** skill body only + this-phase `memory.db` facts.
2. **Prior phases become short durable notes** - not raw tool dumps and not unbound skill bodies carried forward (qwen context tax / theatre).
3. **Proof**: phase N+1 prompt excludes unbound skill bodies and prior-phase tool dumps.
4. **Align with existing compaction (M12 / CARD-041)** when present; wire into standing Job/Phase Chat + Routines path.
5. **Keep AGENTS.md**: ticked tools still listed every Chat turn (progressive working set must not hide tool schemas).
6. **Not this card**: new Studios, dump-all skill bodies, merging memory into storage.db, inventing a second compaction engine.

### Beat 2: What AutoReiv Does Now
1. Standing Chat `execute_goal_job_phases` appends bound skill bodies and raw phase `output_packet_json` into a growing `accumulated` list passed to every later phase - unbound bodies and tool-ish dumps leak into N+1.
2. CARD-226 rebuilds `prior` from all job-scoped memory.db facts; CARD-228 injects one bound body per phase but leaves prior bodies in `accumulated`.
3. Routines standing path appends `content[:500]` into `prior` without stripping tool dumps or separating bound skill bodies.
4. M12 `ContextCompactor` already truncates oversized tool outputs and condenses intermediate turns for Chat sessions - standing Job/Phase assignment prompts do not reuse that discipline.

### Beat 3: What Will Change
1. Add `working_set_context` assembler: per-phase working set = goal + matched metadata + this-phase bound skill body + this-phase memory facts + prior durable notes.
2. Distill completed phases into short durable notes (tool-dump stripped / M12-aligned truncation); never carry unbound skill bodies forward.
3. Wire Chat standing loop + crash-resume remaining phases + Routines standing path through the assembler (replace raw `accumulated` / `prior.append(content)` theatre).
4. TDD red->green proof that phase N+1 excludes unbound skill bodies and prior tool dumps; scorecard + CHANGELOG; push `feat/*` only.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-WSCTX-001]**: Each Job/Phase turn working set includes phase goal + matched metadata + bound skill body only + this-phase memory.db facts.
- [x] **[REQ-WSCTX-002]**: Prior phases contribute short durable notes only (not raw tool dumps / unbound skill bodies).
- [x] **[REQ-WSCTX-003]**: Proof - phase N+1 prompt excludes unbound skill bodies and prior-phase tool dumps.
- [x] **[REQ-WSCTX-004]**: Align with existing M12 / ContextCompactor truncation discipline (reuse patterns; no parallel compaction product).
- [x] **[REQ-WSCTX-005]**: Wired into standing Job/Phase Chat and Routines paths.
- [x] **[REQ-WSCTX-006]**: AGENTS.md invariant - Chat still lists ticked tools every turn (working set does not hide tool schemas).
- [x] **[REQ-WSCTX-007]**: Automated tests red->green; ruff clean; CHANGELOG + scorecard; push `feat/*` only - never qa/main. Live proof on Jarvis -> Done when holds.

---

## 3. Constraints & Honor Flags

- Branch: `feat/standing-job-graph-runtime`. Never merge/push qa/main.
- Anti-theatre: real phase-scoped prompts + proof that N+1 is clean.
- Out of scope: new Studios, second compaction engine, hiding Chat tools behind skills.

## 4. Modules Likely Touched

- `src/application/orchestration/working_set_context.py` (new)
- `src/application/orchestration/chat_job_binding.py` (prompt formatting)
- `src/web/routers/chat.py` (standing + resume loops)
- `src/application/routines/executor.py` (standing phases)
- `tests/unit/orchestration/test_phase_scoped_working_set.py`
- `notes/marathon-scorecard-standing-job-graph.md`, `CHANGELOG.md`

## 5. Marathon Build Lock

- TDD: red "phase N+1 excludes unbound skill bodies and prior-phase tool dumps" first, then green.
- Extend standing path + M12 truncation patterns - do not invent a parallel context product.

## 6. Marathon Build Notes (Jarvis 2026-09-11 ET)

- New `working_set_context`: per-phase working set = goal + matched metadata + bound skill body only + this-phase memory.db facts + prior durable notes.
- `distill_durable_note` / `strip_tool_dumps` align with M12 ContextCompactor truncation (`M12_MAX_TOOL_CHARS=8000`, TRUNCATED markers).
- Chat `execute_goal_job_phases` + crash-resume remaining phases + Routines standing path wired; bound bodies stay phase-local (never accumulate into prior).
- AGENTS.md: working set shapes assignment prompt only; Chat still mounts ticked tools every turn.
- Tests: `tests/unit/orchestration/test_phase_scoped_working_set.py` (5) green; related memory/skill/compaction suites green; ruff clean.
- Live smoke PASS: `notes/marathon-card229-live-smoke.json` (N+1 excludes unbound body + tool dump).
- Status: **Done** (unit + live proof); push `feat/*` only.
