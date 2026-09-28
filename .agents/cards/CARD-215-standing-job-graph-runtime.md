# [CARD-215] Standing Job-Graph Runtime (Retire Per-Prompt Goal Mode)

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: Design room B→C lock (simple first); extends Job/Phase (CARD-096–101), Reflexion (CARD-013/064), chat binding
> **Labels**: `type:architecture`, `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Jobs run themselves**: When Jacob asks for a high-level outcome in Chat, AutoReiv should plan and keep going through research → plan → verify → build / handoff **without** him flipping a "Goal mode" or "Plan-and-execute" switch on every message.
2. **One source of truth for the plan**: The lasting plan lives in Job/Phase records he can see (Chat status strip / Observability), not in a parallel goal API that can disagree with what Chat shows.
3. **Honest verify**: Self-check / Reflexion only runs when there is a **real external check** (test, schema, health probe, checker name that actually fails closed). Same-model "looks good" critique alone is not enough.
4. **Not this card**: The "what can we do?" capability catalog is the **next** slice (C). Do not build it here.

### Beat 2: What AutoReiv Does Now
1. **Split brain**: `JobPhaseOrchestrator` + chat Job/Phase binding persist durable phases, **and** `PlanAndExecuteEngine` still powers per-prompt `goal_mode` plus `POST /api/chat/goal` (`src/web/routers/chat.py`, `src/application/kernel/plan_engine.py`, wired in `src/web/app.py`).
2. **UI toggle theatre**: Chat can send `goal_mode: true` / `self_verify: true`. Standing runtime does **not** choose research→plan→verify→build; Jacob does via flags.
3. **Reflexion partial**: `ReflexionLoopEngine` + `run_verified_turn` exist; without a binary external verifier, retries are same-model critique theatre.
4. **What stays**: Kernel ReAct (`AgentKernel`), HITL park/resume for dangerous tools, A2A handoff, MCP as tool transport, Routines scheduler — extend these, do not replace them.

### Beat 3: What Will Change
1. **Job/Phase is the only durable plan store** for multi-step outcomes. Runtime (not a Chat toggle) decides when to formulate/advance/replan phases.
2. **Standing decision (no new mode name):** multi-step outcomes → formulate / advance / replan via `JobPhaseOrchestrator`; short tool turns stay plain `AgentKernel` ReAct. Do not invent another user-facing or request-flag "mode" under a different name.
3. **`PlanAndExecuteEngine` may remain** only as a **no-tool phase formulator** that writes into Job/Phase — never a second execute path beside kernel ReAct + Job/Phase. `execute_plan` / parallel goal execute authority is retired.
4. **Retire authority of** per-prompt `goal_mode` and parallel `/api/chat/goal` (remove UI toggle + stop treating them as the plan authority; deprecate or thin-wrap to Job/Phase only if needed for one release).
5. **Reflexion policy**: run verify/retry only when a named external verifier/checker is present and executable; otherwise skip verify honestly (no fake pass).
6. **Operator path**: Chat Job/Phase strip + Observability remain how Jacob sees progress, park, fail, and resume. HITL stays on dangerous tools, not on "enter plan mode."
7. **Proof**: failing tests first for "no toggle required for multi-phase job" and "verify skipped without checker"; then green. Live QA runbook on `grok` / feat branch.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **[REQ-JOBGRAPH-001]**: A multi-step Chat outcome creates/advances durable Job + Phase rows via `JobPhaseOrchestrator` without requiring `goal_mode=true` on the request.
- [x] **[REQ-JOBGRAPH-001a]**: Standing routing is explicit in code/docs: multi-step → Job/Phase orchestrator; short turns → kernel ReAct only — no replacement Chat toggle or request flag that reintroduces mode theatre.
- [x] **[REQ-JOBGRAPH-001b]**: If `PlanAndExecuteEngine` remains, it is limited to no-tool phase formulation into Job/Phase; `execute_plan` / `/api/chat/goal` execute authority is removed or thin-wrapped so it cannot bypass Job/Phase + kernel.
- [x] **[REQ-JOBGRAPH-002]**: Per-prompt `goal_mode` is removed from Chat UI authority; `/api/chat/goal` is deprecated or redirected so it cannot create a plan store that bypasses Job/Phase.
- [x] **[REQ-JOBGRAPH-003]**: `self_verify` / Reflexion retries execute only when an external verifier/checker is configured; missing checker → honest skip (no same-model-only success).
- [x] **[REQ-JOBGRAPH-004]**: Operator can see phase status, park/fail, and resume from Chat (and Observability where already wired) without a second goal dashboard.
- [x] **[REQ-JOBGRAPH-005]**: MCP remains transport only (no orchestrator role). HITL policy gate unchanged for dangerous tools.
- [x] **[REQ-JOBGRAPH-006]**: Automated tests: red then green for 001–003; ruff/eslint clean; preflight not required green until Jacob says build and DoD run.
- [x] **[REQ-JOBGRAPH-007]**: CHANGELOG `[Unreleased]` updated; work stays on `feat/*` cut from `grok` — **never merge to `qa`/`main`**.

---

## 3. Constraints & Honor Flags

- Status: **Ready**. Do not set In Progress or write product code until Jacob explicitly says **build**.
- Branch: `feat/standing-job-graph-runtime` (or successor) off **`grok` only**. Never merge to `qa` or `main`.
- Out of scope: capability-map catalog (slice C), CARD-116 memory write-path, ATF/Lab, Homelab/OpenTofu domain outcomes as product features.
- Anti-theatre: every AC must name durable state (Job/Phase SQLite), Studio path (Chat strip), failure mode, and test/live proof.
- Align with AGENTS.md primitives: Skill = SKILL.md, Tool = callable, Pack = one agent, Platform ≠ Global, storage.db ≠ memory.db.

---

## 4. Modules Likely Touched (inventory only — not a build plan)

- `src/web/routers/chat.py` — `goal_mode` / `self_verify` / `/api/chat/goal`
- `src/application/kernel/plan_engine.py` — `PlanAndExecuteEngine` (formulator-only if kept; no second execute path)
- `src/application/orchestration/job_phase_orchestrator.py` + chat job binding
- `src/application/kernel/reflexion_engine.py` + `AgentKernel.run_verified_turn`
- Chat SPA goal/verify toggles under `src/web/static/modules/`
- Tests under `tests/` mirroring Job/Phase + verify skip policy

---

## 5. Human QA Runbook (after build)

1. Reload Chat on the feat/`grok` stack.
2. Send a multi-step ask **without** Goal mode — confirm Job/Phase strip advances.
3. Confirm Goal mode toggle is gone or inert.
4. Turn on verify **without** a checker — confirm honest skip, not fake pass.
5. Trigger a dangerous tool — HITL still parks.

## 6. Marathon Live QA (Jarvis 2026-09-10)

- Boot: `deploy/windows/run_autoreiv.ps1` → http://127.0.0.1:8000 (health ok)
- Ollama: `qwen3.8:latest` @ http://192.168.1.29:11434
- Multi-step without goal_mode: Job+3 phases created/advanced (p0 running) — PASS
- Short ask: turn_done, jobs=0 — PASS
- Goal toggle absent in HTML (`goalToggle` not present); chat.js forces goal_mode:false — PASS
- self_verify without checker: `reflexion_verified` status skipped / skipped_no_checker, passed=false — PASS
- Dangerous tool HITL: not live-triggered; path present in `HITLApprovalEngine` / kernel / unit tests — NOTED
- Automated: unit+integration standing job graph 8 passed
