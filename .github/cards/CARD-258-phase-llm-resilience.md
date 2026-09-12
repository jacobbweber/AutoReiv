# [CARD-258] Phase LLM Resilience — Longer Budget + Retries (P0)

> **Status**: Ready
> **Created**: 2026-09-12
> **Spec Reference**: Architect Done bars after live FAIL job_cbf0a330fc5c — Formulate `phase_llm_timeout after 120.0s` (created 04:16:29Z / failed 04:18:29Z). Chat honesty from CARD-257 held ("Not done"). CoS ranked: (1) timeout most likely (2) empty Wiki quality not this badge (3) no repo tools out of scope. Tip: feat/self-scaffold-queue-e2e-255 @ 20d2725 (257 Research-skip + rail fix included).
> **Labels**: type:bug, P0, ControlPlane, PhaseLLM, Resilience, AntiTheatre
> **Branch**: `feat/self-scaffold-queue-e2e-255` (work ON tip; push; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Live Job `job_cbf0a330fc5c` FAILED Formulate with `phase_llm_timeout after 120.0s`. Execute stayed queued. Chat was honest ("Not done") — CARD-257 status honesty held; the kill is the wait budget, not theatre.
2. qwen on Nimo (192.168.1.29) has slow KV fill. 120s is too short. Operator `.env` already had `STANDING_PHASE_LLM_TIMEOUT_SECONDS=1800` but serve used the **import-time default of 120** (CLI never loads `.env`; constant frozen at import).
3. Need a longer default budget for slow KV **and** 1–2 retries on `phase_llm_timeout` / connection stall **before** fail.
4. After retries exhausted → park or FAILED with a clear reason — **never Done / invent a Wiki note**.
5. This card is **ONLY** LLM wait/retry — not Wiki-thin quality, not repo agents.

### Beat 2: What AutoReiv Does Now
1. `STANDING_PHASE_LLM_TIMEOUT_SECONDS` default `120`, read once at import. Chat `_stream_turn_bound` and routine executor `wait_for` that constant.
2. Single attempt: timeout → immediate `fail_phase` (no retry). Connection stall (`ProviderUnavailableError` / httpx network) is a hard fail.
3. `.env` 1800s is ignored: `src/cli/main.py` does not load dotenv; `restart_serve` does not inject `.env` into the child.
4. CARD-257 honesty already emits `Not done` + `job_id` on FAILED — keep that; do not regress to Done-on-FAILED.

### Beat 3: What Will Change
1. **Longer default budget** (300s) sized for qwen KV fill; **resolve at call time** from env so operator `.env` is honored.
2. **Load repo `.env`** on CLI serve / `restart_serve` (never overwrite existing process env).
3. **1–2 retries** on `phase_llm_timeout` and connection stall before fail. Emit `phase_llm_retry` SSE so operators can see attempts.
4. After retries exhausted → FAILED with `retries_exhausted` in the reason + CARD-257 honesty — never Done / invent a note.
5. TDD red→green + CoS live smoke `notes/marathon-card258-live-smoke.json` + 10-scenario stress pack `notes/marathon-card258-stress-pack.json`; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [ ] **[REQ-PLLM-001]**: Formulate / Execute / Research phase LLM under qwen: longer budget for slow KV + 1–2 retries on `phase_llm_timeout` / connection stall before fail.
- [ ] **[REQ-PLLM-002]**: After retries exhausted → park or FAILED with a clear reason (`retries_exhausted`) — never Done / invent a Wiki note.
- [ ] **[REQ-PLLM-003]**: This card is ONLY LLM wait/retry — not Wiki-thin quality, not repo agents.
- [ ] **[REQ-PLLM-004]**: Live proof: CoS standing-Job prompt under loaded Ollama completes Formulate→Execute (or parks after retries with honesty). Artifact `notes/marathon-card258-live-smoke.json`.
- [ ] **[REQ-PLLM-005]**: Tests red→green; CHANGELOG; push on `feat/self-scaffold-queue-e2e-255` only — never qa/main; do not merge to grok. 10-scenario stress pack `notes/marathon-card258-stress-pack.json`.

## 3. Constraints

- Work ON `feat/self-scaffold-queue-e2e-255` @ 20d2725 tip. feat-off-grok only; never qa/main; never merge grok.
- Honesty never Done-on-FAILED (CARD-257). Quality > speed.
- Do not invent a second orchestrator. Extend standing Chat + routine executor wait.

## 4. Modules Likely Touched

- `src/application/orchestration/phase_llm_resilience.py` (new: resolve/retry/classify)
- `src/application/orchestration/standing_job_graph.py` (default budget + re-export)
- `src/web/routers/chat.py` (retry loop + `phase_llm_retry` SSE)
- `src/application/routines/executor.py` (same retry policy)
- `src/cli/main.py` + `scripts/restart_serve.py` (load `.env`)
- `tests/unit/orchestration/test_card258_phase_llm_resilience.py` (new)
- `tests/unit/routines/test_routine_standing_job_path.py` (timeout test honors retries)
- `CHANGELOG.md`, `notes/marathon-card258-live-smoke.json`, `notes/marathon-card258-stress-pack.json`

## 5. CoS smoke prompt

```
Write a short Wiki note in 00_Inbox explaining what a standing Job is in AutoReiv (phases Formulate then Execute, done-when, and why HITL parks on create). Done-when: I can open that note via wiki_note_read. Keep it under 200 words.
```

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD where practical; live Jarvis proof required.
- Do NOT merge to grok/qa/main.
