# [CARD-320] Education Learning OS — Course + Mastery model

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: CARD-316–319 on main/qa (v0.31.0); Architect course-pipeline lock
> **Labels**: type:feature, P0, Education, LearningOS, Course, Mastery, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Education runs as a **durable course**: topic id, ordered Learning OS step list, current step, status — not a one-shot Ask.
2. Each completed step writes a **Wiki artifact** + **ledger anchors** (same memory.db brain as 316–319).
3. **Mastery** is a binary external gate only (quiz/flashcards). Miss → existing Retention `next_due` path (CARD-318/319). No LLM self-score theatre.
4. Restart-safe: same course + step after serve restart.
5. Course pipeline is the **DEFAULT**; mode-picker is secondary jump-to-step only.
6. No Dual Coding chrome on this card (leave Dual Coding for later).

### Beat 2: What AutoReiv Does Now
1. Learning OS steps exist as panels/engines (Priming / Retrieval / Retention / …) but there is **no durable course row**.
2. Inventory (agent `*_memory.db` / education tables — do **not** invent a second tutor runtime):
   - `education_mastery` in agent memory.db (`src/infrastructure/memory/repositories/education_mastery_ops.py`)
   - learner facts via episodic store (`entity=education_learner` / CARD-316–317)
   - **No `education_course` table yet**
3. Prefer **one new table in the same agent memory.db**: `education_course` (topic_id, ordered step list JSON, current_step, status, timestamps) — extend mastery/learner; never storage.db; never a second tutor DB.
4. Course pipeline Architect-locked as DEFAULT; mode-picker jump-to-step stays secondary.

### Beat 3: What Will Change
1. Add `education_course` (or clearly named equivalent) in agent memory.db beside `education_mastery`.
2. Wire Education Studio default path to course pipeline (ordered steps); mode-picker = jump-to-step only.
3. On step complete: Wiki artifact + ledger anchors (reuse Priming/Retrieval write-back patterns).
4. Mastery gate = binary external quiz/flashcards only; miss uses Retention next_due already on qa/main.
5. Prove restart-safe course+step; TDD first; no Dual Coding UI.

---

## 2. Acceptance (Research/Architect lock)

- [x] **[REQ-EDU-COURSE-001]**: Durable course row: `topic_id`, ordered Learning OS step list, `current_step`, `status` in agent memory.db table **`education_course`** (named in this card; inventory confirmed no prior course table — extend memory.db, do not invent a second tutor runtime).
- [x] **[REQ-EDU-COURSE-002]**: Each completed step writes Wiki artifact + ledger anchors (education_mastery / learner facts as appropriate).
- [x] **[REQ-EDU-COURSE-003]**: Mastery = binary external gate only (quiz/flashcards); miss → Retention `next_due` path (CARD-318/319).
- [x] **[REQ-EDU-COURSE-004]**: Restart-safe: same course + step after serve restart.
- [x] **[REQ-EDU-COURSE-005]**: Course pipeline is DEFAULT; mode-picker is secondary jump-to-step only.
- [x] **[REQ-EDU-COURSE-006]**: Proof: failing test → green; live smoke on Jarvis. No Dual Coding chrome. No toast-only Done.

---

## 3. Constraints

- Branch `feat/education-studio-finish` off new main tip (or qa if synced). Never merge `main` unless Jacob asks. Hold FF→`qa` until **merge to qa**.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- No Dual Coding on this card.
- Do not invent a second tutor runtime / storage.db education store.

---

## 4. Out of scope

- Dual Coding chrome / amplifiers polish
- Adaptive SRS beyond existing 1-3-7-30
- Capability-gap smoke (follow-on)

---

## 5. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-320**)
- After live OK → Jacob: **merge to qa**
