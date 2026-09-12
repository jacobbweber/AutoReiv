# [CARD-247] Education Analysis (error log + metacog facts)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Analysis: Error log + metacog facts in memory.db. Live: Miss reasons feed next quiz set. Research: binary external verify + Wiki/memory.db write-back.
> **Labels**: type:feature, P1, Education, Analysis, AntiTheatre
> **Branch**: `feat/education-analysis-247` (off `feat/education-application-246` @ 85432f4)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants **Analysis**: after a miss/fail, AutoReiv must remember **why** it was wrong - an **error log + metacog facts** in agent memory.db - not just a thin miss count.
2. Live: those **miss reasons must feed the next quiz set** (deepen CARD-243 weak-item pressure) so the learner is drilled on the failure pattern, not a random strong item.
3. Research Done bar: keep **binary external verify** (no LLM self-score theatre) and durable **Wiki and/or memory.db write-back** of analysis outcomes.
4. Education Studio needs an operator path to **view the error log / patterns** - not chat-only theatre.

### Beat 2: What AutoReiv Does Now
1. CARD-242..246 ship quiz/elaboration/application binary grade + mastery ledger + learner strengths/weaknesses/patterns + Studio panels.
2. On miss, mastery + learner weakness facts update, but there is **no structured error log** (expected vs given, miss_reason taxonomy) and no metacog fact beyond thin pattern strings.
3. Quiz selection prefers due/weak item_ids (CARD-243) but does **not** consume miss-reason / error-pattern pressure across related items.
4. Education Studio has Quiz / Elaboration / Construction / Application - no Analysis / error-log operator path.

### Beat 3: What Will Change
1. Analysis engine: on miss/fail, classify a **binary miss_reason** (deterministic, no LLM) and write **error_log + metacog** semantic facts into agent memory.db.
2. `select_quiz_items` / quiz next consumes those miss reasons so the next quiz set pressures the failure pattern (feeds CARD-243 weak pressure).
3. Optional Wiki write-back of analysis summary; memory.db is mandatory for durability.
4. Education Studio Analysis panel + `/api/education/analysis/*` to view error log / patterns.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-AN-001]**: On quiz/application/elaboration miss/fail, record durable **error log + metacog facts** in agent `memory.db` (never `storage.db`), including item_id, expected vs given (or concept gaps), and a binary-classified `miss_reason`.
- [x] **[REQ-EDU-AN-002]**: Next quiz selection uses those **miss reasons** to pressure related weak items (feeds CARD-243 weak-item pressure) - not random / first-extracted-only when error patterns exist.
- [x] **[REQ-EDU-AN-003]**: Analysis outcome write-back lands in Wiki and/or agent `memory.db`. Grade/analysis remains **binary external** - LLM self-score is not Done.
- [x] **[REQ-EDU-AN-004]**: Education Studio operator path to view error log / patterns (`/api/education/analysis/*`) - not chat-only theatre.
- [x] **Proof**: pytest + Studio path + `notes/marathon-card247-live-smoke.json` with miss -> reason logged -> next quiz set reflects it.

## 3. Constraints

- Continue marathon feat stack on `feat/education-analysis-247` off 246 tip @ 85432f4. Never qa/main. Do **not** merge to grok.
- Reuse mastery / learner-model / memory.db primitives. Do **not** invent a second tutor runtime.
- Binary / deterministic miss_reason classification only - no same-model self-score theatre.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Lumina / concept-player visuals remain OUT.
- Do **not** start CARD-248 in this task.

## 4. Out of scope (follow-on)

- LLM-authored free-form metacognition essays as the primary scorer.
- Cross-learner / fleet-wide error analytics dashboards.
- Lumina / concept-player visuals.
- CARD-248+.

## 5. Proof (when building)

- Pytest: miss writes error_log + metacog facts; select_quiz prefers miss-reason pressure; no LLM in analysis module; Wiki/memory write-back.
- Studio: Analysis panel wired to `/api/education/analysis/*`.
- Live: notes/marathon-card247-live-smoke.json.
