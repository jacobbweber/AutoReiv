# [CARD-318] Education Learning OS — Retrieval (binary external grade → ledger)

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-retrieval-318` (off `qa` @ c04f56b)
> **Depends**: CARD-242 quiz + SRS; CARD-316 learner ledger; CARD-317 Priming write-back (Wiki + anchors)
> **Labels**: type:feature, P0, Education, LearningOS, Retrieval, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. After Priming leaves a schema note + ledger anchors, he must **practice recall** — not re-read the note and call it learned.
2. Practice answers are graded by a **binary external** checker (exact / normalized match — not LLM “looks right”).
3. Pass/fail writes into the same item×mastery row in `memory.db`; a miss sets `next_due` on **1-3-7-30**.
4. No new Education chrome — use existing quiz / due / learner surfaces.

### Beat 2: What AutoReiv Does Now
1. CARD-242/316: `grade_answer_binary` + `POST /api/education/quiz/grade` → `record_education_grade` → miss schedules `next_due`; learner summary exists.
2. CARD-317: Priming write-back seeds unseen mastery anchors from the Wiki Priming note.
3. Gaps to prove/harden: Priming-seeded anchors are actually practiced end-to-end; grade path stays binary-external; miss updates the **same** row; Education learner summary matches after restart. Retention Routine→Job polish is the **next** card, not this one.

### Beat 3: What Will Change
1. Prove-and-harden Retrieval: practice item → binary external grade → write pass/fail to item×mastery; miss sets `next_due` (1-3-7-30).
2. Prefer Priming-seeded (or quiz-extracted) items — same ledger, no second store.
3. TDD + live smoke: same row after restart; learner summary matches. No new Studio panels.

## 2. Acceptance (Architect + Research locked)

- [ ] **[REQ-EDU-RET-001]**: Practice path grades with **binary external** checker (`grade_answer_binary` / rubric — never LLM self-score); response exposes `grader: binary_external` (or equivalent).
- [ ] **[REQ-EDU-RET-002]**: Pass/fail writes durable item×mastery in agent `memory.db` (`grade`, `last_graded_at`, miss/pass counts).
- [ ] **[REQ-EDU-RET-003]**: Miss sets `next_due` on fixed **1-3-7-30** (stage 0 → +1 day on first miss).
- [ ] **[REQ-EDU-RET-004]**: Priming-seeded or extractable practice items can be graded; Education learner / mastery APIs show the updated row (no toast-only theatre).
- [ ] **[REQ-EDU-RET-005]**: Proof: after restart, same mastery row + learner summary still match. Failing test → green; live smoke on Jarvis (Qwen Ask optional).
- [ ] **No new Education chrome** (UX lock).

## 3. Constraints

- Branch `feat/education-retrieval-318` off `qa` only. Never merge `main` unless Jacob asks. Hold FF→`qa` until **merge to qa**.
- Extend CARD-242/316/317 primitives (`quiz_engine`, `education_mastery_ops`, `/api/education/quiz/*`) — do not invent a second grader or ledger.
- Retention Routine→Job deepen is **out of scope** (follow-on card).
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- No product code on this scaffold commit — Status **Ready** until Jacob says **build**.

## 4. Out of scope

- Retention Routine→Job polish (next wave)
- Amplifiers / Lumina / new quiz UI panels
- Adaptive SRS beyond 1-3-7-30

## 5. Wave order

1. CARD-317 Priming write-back — **Done on qa**
2. **This card** — Retrieval binary grade
3. Retention Routine→Job
4. Capability-gap smoke → horizon triage

## 6. Reply phrases

- Scaffold done → Jacob: **build** (or **build CARD-318**)
- After live OK → Jacob: **merge to qa**
