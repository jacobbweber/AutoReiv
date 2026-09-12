# [CARD-249] Education Visual Amplifiers (Mermaid / step-through on Retrieval)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Visual amplifiers: Dual-coding Mermaid/step-through on real pedagogy signal. Live: Amplifier never ships without Retrieval path. Research: 249 last mandatory; amplifiers without Retrieval = edutainment. Skip Lumina film as P0.
> **Labels**: type:feature, P1, Education, DualCoding, Retrieval, AntiTheatre
> **Branch**: `feat/education-visual-amplifiers-249` (off `feat/education-environment-248` @ 33e2617)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants **visual amplifiers** that deepen Dual Coding / Retrieval - Mermaid diagrams and **step-through** reveals on real quiz/mastery items.
2. Live: an amplifier **never ships without a Retrieval path** (quiz item + mastery ledger). Visuals-only = edutainment and must be refused.
3. Research Done bar: CARD-249 is the last mandatory Learning OS slice; amplifiers without Retrieval are theatre.
4. Skip Lumina / concept-player film as P0 - Mermaid + step-through only.
5. Education Studio needs an operator path to attach/preview amplifiers on Retrieval-backed items - not chat-only theatre.

### Beat 2: What AutoReiv Does Now
1. CARD-238 Dual Coding writes prose + Mermaid to Wiki; CARD-242..248 ship quiz, mastery ledger, SRS, learner model, elaboration, construction, application, analysis, environment.
2. Mermaid lives in Dual Coding notes but is **not** attached as a pedagogy amplifier to quiz/mastery Retrieval items.
3. There is no step-through reveal of Dual Coding diagrams tied to due/weak quiz prompts.
4. Nothing refuses a visuals-only path that skips Retrieval.

### Beat 3: What Will Change
1. Visual amplifier engine: extract Mermaid (+ optional ## Step-through) from Dual Coding / study notes and build ordered step-through reveals.
2. Amplifiers **require** a mastery/quiz `item_id` (Retrieval path). Attach/persist linkage in agent memory.db; reject visuals-only payloads.
3. Quiz/next and Studio can surface amplifier Mermaid + step-through beside Retrieval-backed items (presentation aid - ledger/SRS unchanged).
4. Education Studio Visual Amplifiers panel + `/api/education/amplifiers/*`. No Lumina film.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-VA-001]**: Mermaid and/or step-through visual amplifiers extract from Dual Coding / study notes and attach to existing quiz/mastery **Retrieval** items (real pedagogy signal - not orphan diagrams).
- [x] **[REQ-EDU-VA-002]**: Amplifier **never ships without Retrieval path** - missing `item_id` / unknown mastery row / visuals-only mode is refused (amplifiers without Retrieval = edutainment).
- [x] **[REQ-EDU-VA-003]**: Step-through reveals ordered pedagogy steps from Mermaid (or explicit Step-through section); Lumina / concept-player film remains OUT of P0.
- [x] **[REQ-EDU-VA-004]**: Education Studio operator path (`/api/education/amplifiers/*` + panel) to extract/attach/preview amplifiers on Retrieval-backed items - not chat-only theatre.
- [x] **Proof**: pytest + Studio path + `notes/marathon-card249-live-smoke.json` with visual on a Retrieval-backed item and refusal without quiz/ledger path.

## 3. Constraints

- Continue marathon feat stack on `feat/education-visual-amplifiers-249` off 248 tip @ 33e2617. Never qa/main. Do **not** merge to grok.
- Reuse Dual Coding Mermaid + CARD-242 quiz/mastery Retrieval primitives. Do **not** invent a second due engine or visuals-only tutor mode.
- Amplifiers never call `record_education_grade` or rewrite `next_due` (presentation + pedagogy signal only).
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Skip Lumina film as P0.
- Do **not** invent CARD-250.

## 4. Out of scope (follow-on)

- Lumina / concept-player film / video.
- Auto-generating Mermaid via LLM at quiz time (extract from Wiki Dual Coding notes only).
- Replacing quiz/SRS with diagram-only study.
- CARD-250+.

## 5. Proof (when building)

- Pytest: extract Mermaid/step-through; attach requires mastery item; visuals-only refused; quiz presentation can include amplifier; no SRS mutation.
- Studio: Visual Amplifiers panel wired to `/api/education/amplifiers/*`.
- Live: notes/marathon-card249-live-smoke.json.
