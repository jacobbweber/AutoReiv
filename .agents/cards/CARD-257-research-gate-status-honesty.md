# [CARD-257] Research Gate Skip-or-Continue + Status Honesty (P0)

> **Status**: Done
> **Created**: 2026-09-12
> **Spec Reference**: Architect Done bars after live FAIL job_a80bc2385bbe — Research hard-fail below_threshold:1<2 + Chat Done theatre. CARD-231 was insert Research then Formulate, NOT fail-closed kill. Tip: feat/self-scaffold-queue-e2e-255 @ dfc96e1.
> **Labels**: type:bug, P0, ControlPlane, ResearchGate, AntiTheatre, StatusHonesty
> **Branch**: `feat/self-scaffold-queue-e2e-255` (work ON tip; push; never merge grok/qa/main)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Live Job `job_a80bc2385bbe` FAILED in Research on `below_threshold:1<2` (matched `tool.wiki_note_read` only). Formulate/Execute stayed queued. Root kill: Research LLM `phase_llm_timeout after 120s` → `fail_phase` dead-end.
2. Chat assistant said **"Done. The note exists..."** (and invented/claimed unrelated `00_Inbox/okta_sso_how_it_works.md`) while Journey showed **FAILED** — status theatre.
3. Architect lock: if matched `wiki_note_*` (or other tools) already **cover the outcome**, **skip Research** or continue to Formulate — **never hard-fail the Job on thin match alone**. CARD-231 = insert then Formulate, not fail-closed kill at 1<2.
4. Live proof: CoS standing-Job prompt → Research skipped or green → Formulate→Execute → note in `00_Inbox/` + Journey success on same `job_…`.
5. Chat must not say Done / invent a note when Journey/job is FAILED.

### Beat 2: What AutoReiv Does Now
1. `assess_catalog_match` returns thin/`research_inserted` on `count < 2` **before** checking whether matched tools already cover implied critical families.
2. Standing mint inserts Research + runs `run_standing_research` side-effects, then Chat still runs an **LLM Research phase** that can timeout → `fail_phase` kills the whole Job.
3. On phase fail, SSE may already have streamed LLM "Done…" tokens; early `return` leaves that theatre as the visible assistant claim.
4. `derive_success_rule` can latch onto bare `done-when,` inside parentheticals (garbled rule on the live FAIL) instead of colon-form `Done-when: …`.

### Beat 3: What Will Change
1. **Coverage short-circuit**: when matched tools cover all implied critical families, treat as **sufficient** (`outcome_covered_by_matched`) even if `count < SUFFICIENT_MATCH_MIN` — skip Research.
2. **Research auto-complete**: when Research was inserted and side-effects already ran, standing Chat **auto-completes Research without LLM** and advances to Formulate — never timeout-kill on thin match alone.
3. **Status honesty**: on Job/phase FAILED, emit corrective assistant `turn_done` (job_id + phase + reason) — never leave "Done" / invented note as the final claim.
4. **Done-when parse**: prefer colon-form `Done-when:` / `done when:` clauses over bare `done-when,` fragments.
5. TDD red→green + CoS live smoke `notes/marathon-card257-live-smoke.json`; CHANGELOG; push feat tip only.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-RGATE-001]**: Matched tools covering the outcome (e.g. `wiki_note_*` for wiki done-when) → **skip Research** or continue to Formulate; never hard-fail Job solely on `below_threshold:N<2`.
- [x] **[REQ-RGATE-002]**: Thin Research path that still inserts Research auto-completes (side-effects already at mint) without LLM timeout → Formulate→Execute can run.
- [x] **[REQ-RGATE-003]**: Status honesty — Chat must not claim Done / invent a note when Journey/job is FAILED; emit honest failure content with `job_id`.
- [x] **[REQ-RGATE-004]**: Live CoS standing-Job prompt → Research skipped or green → Formulate→Execute → note in `00_Inbox/` + Journey success; artifact `notes/marathon-card257-live-smoke.json`.
- [x] **[REQ-RGATE-005]**: Tests red→green; CHANGELOG; push on `feat/self-scaffold-queue-e2e-255` only — never qa/main; do not merge to grok. Confirm rail still mounts after `restart_serve`.

## 3. Constraints

- Work ON `feat/self-scaffold-queue-e2e-255` @ dfc96e1 tip. feat-off-grok only; never qa/main; never merge grok.
- Catalog-matched tools; `memory.db` ≠ `storage.db`; toast ≠ proof.
- Extend CARD-231 heuristic + standing Chat path — do not invent a second orchestrator.

## 4. Modules Likely Touched

- `src/application/orchestration/research_before_plan.py` (coverage short-circuit)
- `src/application/orchestration/outcome_intake.py` (Done-when colon preference)
- `src/web/routers/chat.py` (Research auto-complete + status honesty)
- `tests/unit/orchestration/test_research_before_plan.py`
- `tests/unit/orchestration/test_outcome_intake.py`
- `tests/unit/orchestration/test_card257_research_gate_honesty.py` (new)
- `CHANGELOG.md`, `notes/marathon-card257-live-smoke.json`

## 5. CoS smoke prompt

```
Write a short Wiki note in 00_Inbox explaining what a standing Job is in AutoReiv (phases Formulate then Execute, done-when, and why HITL parks on create). Done-when: I can open that note via wiki_note_read. Keep it under 200 words.
```

## 6. Marathon Build Lock

- Architect Done bars locked — Builder implements now.
- TDD where practical; live Jarvis proof required.

## 7. Marathon Build Notes (Jarvis 2026-09-11 ET / 2026-09-12 UTC)

- Root cause: `assess_catalog_match` fail-closed thin at `1<2` before coverage check; Research LLM `phase_llm_timeout` → `fail_phase` killed Job; Chat streamed Done tokens (status theatre). Live FAIL `job_a80bc2385bbe`.
- Fix: `outcome_covered_by_matched` skip Research; `auto_complete_prepared_research` (no LLM); `format_job_failed_honesty`; colon-form Done-when parse.
- Commits: `9ab4085` (scaffold), `459db5f` (fix).
- Live proof: `job_e332939825bf` DONE; Research skipped (`outcome_covered_by_matched`); Formulate→Execute done; note `00_Inbox/standing_job_in_autoreiv.md`; `notes/marathon-card257-live-smoke.json`.
- Rail: `restart_serve` tip `459db5f`; health ok; `chat.js` 200 + journey chrome present.
- Status: **Done**; push feat tip only — never qa/main/grok merge.
