# [CARD-316] Education Learning OS — durable learner ledger (prove + harden)

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/education-learning-os` (off `qa` @ 41add85)
> **Depends**: CARD-242 mastery ledger, CARD-243 learner pressure (claimed Done on prior marathon); CARD-315 shell
> **Labels**: type:feature, P0, Education, LearningOS, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Start the **Education Learning OS** dig — knowledge that sticks as a second mind, not more Studio panels.
2. First slice: a **durable learner ledger** he can trust after restart (strengths, weaknesses, mastery / next review).
3. Misses must come back on a spaced schedule; Education (and Observe if already wired) show the **same** durable facts — not a toast.
4. Live proof on **Qwen Spark** — not demo theatre.

### Beat 2: What AutoReiv Does Now
1. CARD-242/243 on `qa` already ship `education_mastery` in agent `memory.db` (`item_id`, topic, grade, `interval_stage`, `next_due`), binary quiz grade APIs, learner summary, and Ask pressure helpers.
2. Education Studio shell (CARD-315) collapses Learning OS panels; no new mastery chrome.
3. Gaps to prove/harden on current `qa` tip: live miss → `next_due` on **1-3-7-30** survives kill/resume; Education UI + `/api/education/learner` (and Observe if present) show the same rows; no LLM self-score as mastery.

### Beat 3: What Will Change
1. Prove-and-harden the durable **item × mastery** ledger (not a parallel tutor runtime).
2. Closing any real gaps so Architect Done bar is true on `qa` with failing→green tests + live Qwen smoke.
3. Document follow-on wave: Priming write-back → Retrieval binary external grade harden → Retention Routine→Job. **Park amplifiers** until this ledger is proven.

## 2. Acceptance (Architect + Research locked)

- [x] **[REQ-EDU-LOS-001]**: Durable store = **item × mastery** rows in Education / agent `memory.db` (never `storage.db`): at least `item_id`, topic/path, grade, strength/weakness tags or equivalent learner facts, last result, **`next_due` / next_review_at**.
- [x] **[REQ-EDU-LOS-002]**: Ask or practice (quiz grade) **writes a real ledger row**; miss schedules next review on **1-3-7-30** in the ledger (Routine→Job may already exist from 242 — ledger must hold `next_due` now).
- [x] **[REQ-EDU-LOS-003]**: Education Studio (and Observe if already showing education facts) can read back the **same** durable facts — not session-only UI / toast.
- [x] **[REQ-EDU-LOS-004]**: Grade remains **binary external** — never LLM self-score as mastery.
- [x] **[REQ-EDU-LOS-005]**: Kill/resume or restart serve: miss still resurfaces (`next_due` + quiz/next or Ask pressure) from `memory.db`.
- [x] **Proof**: Failing test → green; live smoke on Qwen Spark — miss → peek ledger → restart → due/pressure still that miss.

## 3. Constraints

- Branch `feat/education-learning-os` off `qa` only. Never merge `main` unless Jacob asks. Hold FF→`qa` until he says **merge to qa**.
- Extend CARD-242/243 primitives (`education_mastery_ops`, `/api/education/quiz/*`, `/api/education/learner`) — **do not invent a second tutor runtime**.
- No new mastery chrome panels (UX lock) until this ledger is proven.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Prove-and-harden complete on branch; Status **Done**; merged to qa → merge to qa.

## 4. Out of scope (follow-on cards)

- Priming / Dual Coding write-back deepen
- Retrieval binary-grade harden beyond what’s needed for this proof
- Retention Routine→Job polish (if 242 path already works, prove it; don’t rebuild)
- Amplifiers / Lumina / fake progress chrome
- Adaptive SRS beyond fixed 1-3-7-30

## 5. Wave order after this card

1. Priming write-back  
2. Retrieval with binary external grade  
3. Retention Routine→Job  
Park amplifiers until mastery is real.

## 6. Reply phrases

- Scaffold done → Jacob: **build** (or **build CARD-316**)
- After live OK → Jacob: **merge to qa**

## 7. Executor proof (2026-09-14)

- TDD: `tests/unit/education/test_card316_learner_ledger.py` (+242/243) green
- Gap closed: `record_education_grade` no longer `except: pass` around `record_learner_from_grade`
- Live HTTP smoke (box serve :8000, agent=`assistant`): upsert → grade wrong → `grader=binary_external`, `next_due` +1d, `interval_stage=0`; GET `/api/education/learner` weakness_count≥1; restart_serve → same `next_due` + weakness
- Observe: left alone (no education mastery wiring)
- CHANGELOG: Unreleased note in local tip; remote tip had MCP truncate — restore via `docs/cards/CARD-316-RESTORE-CHANGELOG.md` (from blob `45149d5`)


