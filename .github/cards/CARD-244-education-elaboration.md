# [CARD-244] Education Elaboration (explain-it-back)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Elaboration: explain-it-back vs ledger; fail → resurface; Score ≠ LLM fluff; miss updates ledger; binary external verify + Wiki/memory.db write-back in live proof (LLM self-score ≠ Done)
> **Labels**: type:feature, P1, Education, Elaboration, AntiTheatre
> **Branch**: `feat/education-elaboration-244` (off `feat/education-learner-model-243` @ 7dc6b62)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants **Elaboration / explain-it-back** so Education proves understanding in his own words — not short quiz recall alone.
2. The grade must be a **binary external check** against a reference answer or structured rubric — **LLM self-score is theatre and ≠ Done**.
3. A miss must **update the mastery ledger** and can schedule **Routine → standing Job** resurface (reuse CARD-242 path) — fluff scores that do not touch the ledger fail the Done bar.
4. Live proof must show **Wiki and/or memory.db write-back** of the elaboration outcome (durable second-mind, not chat fluff).

### Beat 2: What AutoReiv Does Now
1. CARD-242/243 ship quiz binary grade + mastery ledger + learner strengths/weaknesses + Routine→Job SRS + weak-preferring quiz/Ask.
2. No explain-it-back / elaboration surface graded against a reference or concept rubric.
3. No elaboration outcome write-back into Wiki notes or memory.db facts beyond quiz grades.
4. Education Studio has Quiz/Due — no Elaboration operator path.

### Beat 3: What Will Change
1. Elaboration engine: extract explain-back prompts (+ reference / required concepts) from Wiki notes; grade with **binary external** check (no LLM).
2. Miss → `record_education_grade` updates mastery ledger + 1-3-7-30; retention Routine can mint standing Job (reuse 242).
3. Pass/miss outcome written back to **Wiki** (append Elaboration outcomes) and/or **memory.db** semantic facts.
4. Education Studio operator path for Load next / explain-back / Grade (binary).

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-ELAB-001]**: Explain-it-back items sourced from Wiki notes (Elaboration / Explain-it-back section, or mastery/quiz prompts with reference); grade is **binary external** via reference equality/containment **or** structured required-concepts rubric. **LLM self-score ≠ Done**.
- [x] **[REQ-EDU-ELAB-002]**: Miss updates the CARD-242 mastery ledger (`grade=miss`, `next_due` on 1-3-7-30) and can schedule Routine→standing Job resurface (reuse education-retrieval-retention path). Chat toast alone is not Done.
- [x] **[REQ-EDU-ELAB-003]**: Elaboration outcome write-back lands in Wiki and/or agent `memory.db` (never `storage.db`). Live proof peeks both when claimed.
- [x] **[REQ-EDU-ELAB-004]**: Education Studio operator path for elaboration (load next, explain-back input, binary grade) — not chat-only theatre.
- [x] **Proof**: Explain-back miss → ledger miss + next_due → (optional) retention mint Job; Wiki/memory.db show outcome write-back; grader module has no LLM complete/gateway/openai/ollama self-score path.

## 3. Constraints

- Continue marathon feat stack on `feat/education-elaboration-244` off 243 tip. Never qa/main. Do **not** merge to grok.
- Reuse mastery ledger + retention Routine→Job (242) + learner facts (243). Do **not** invent a second tutor runtime.
- Binary external grade only — no same-model self-score theatre.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Lumina / concept-player visuals remain OUT.
- Do **not** start CARD-245 in this task.

## 4. Out of scope (follow-on)

- Adaptive free-form semantic graders / embedding similarity as primary score.
- Multi-paragraph essay auto-critique with LLM.
- Lumina / concept-player visuals.
- CARD-245+.

## 5. Proof (when building)

- Pytest: rubric + reference binary grade (no LLM); miss updates ledger + next_due; retention can mint Job; Wiki/memory write-back.
- Vitest / operator: Education Studio elaboration controls present and wired to `/api/education/elaboration/*`.
- Live: notes/marathon-card244-live-smoke.json with miss → ledger + write-back evidence.
