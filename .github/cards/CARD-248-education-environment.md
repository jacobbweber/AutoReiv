# [CARD-248] Education Environment (study-session delivery profiles)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Environment: Study-session mode (tone/timer) as delivery profile only. Live: Does not replace ledger/SRS. Research: ADHD bite-size etc. - never replaces SRS. Delivery-only.
> **Labels**: type:feature, P1, Education, Environment, AntiTheatre
> **Branch**: `feat/education-environment-248` (off `feat/education-analysis-247` @ 01ed49b)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants an **Environment / study-session mode**: pick a **delivery profile** (tone + timer / ADHD bite-size) that shapes how Ask and quiz prompts are *presented*.
2. Live: the profile must **not** replace the mastery ledger or Routine->Job SRS for due/resurface. Delivery-only.
3. Research Done bar: ADHD bite-size and similar session styles are presentation aids - they never invent a second due engine or skip SRS.
4. Education Studio needs an operator path to **pick the profile** - not chat-only theatre.

### Beat 2: What AutoReiv Does Now
1. CARD-242..247 ship quiz, mastery ledger (1-3-7-30), Routine->Job retention, learner model, elaboration, construction, application, analysis.
2. Education Ask modes shape *what* to teach (Priming / Dual / Construction / Application / Analysis) but there is **no study-session delivery profile** (tone / timer / bite-size) for presentation.
3. Due/resurface is correctly owned by the mastery ledger + education-retrieval-retention Routine - and must stay that way.
4. Education Studio has no Environment / session-profile picker.

### Beat 3: What Will Change
1. Environment engine: named **delivery profiles** (tone, timer_seconds, bite_size presentation knobs) that shape Ask clauses and quiz *presentation* only.
2. Applying a profile never mutates `next_due` / interval_stage / mastery grades and never bypasses Routine->Job SRS.
3. Selected profile may be remembered as a preference fact in agent memory.db (delivery preference - not SRS).
4. Education Studio Environment panel + `/api/education/environment/*` to list/select profiles; quiz/next + Ask include delivery presentation metadata.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-ENV-001]**: Study-session **delivery profiles** expose tone + timer / bite-size knobs that shape Ask and quiz *presentation* only (prompt wrapping, session timer hint, bite-size chunking of displayed prompts).
- [x] **[REQ-EDU-ENV-002]**: Applying a profile **does not** replace mastery ledger due/resurface or Routine->Job SRS. `next_due` / interval_stage / due lists remain ledger+SRS sourced regardless of profile.
- [x] **[REQ-EDU-ENV-003]**: ADHD bite-size (and similar research styles) are delivery-only - never a second tutor due engine.
- [x] **[REQ-EDU-ENV-004]**: Education Studio operator path to pick a profile (`/api/education/environment/*`) - not chat-only theatre.
- [x] **Proof**: pytest + Studio path + `notes/marathon-card248-live-smoke.json` with profile applied to Ask/quiz presentation while due/SRS still from ledger.

## 3. Constraints

- Continue marathon feat stack on `feat/education-environment-248` off 247 tip @ 01ed49b. Never qa/main. Do **not** merge to grok.
- Reuse mastery / SRS / Routine->Job primitives. Do **not** invent a second due/resurface runtime.
- Delivery profiles never call `record_education_grade` or rewrite `next_due`.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Lumina / concept-player visuals remain OUT.
- Do **not** start CARD-249 in this task.

## 4. Out of scope (follow-on)

- Replacing 1-3-7-30 with profile-specific due intervals.
- Adaptive due engines driven by ADHD / focus scores.
- Lumina / concept-player visuals.
- CARD-249+.

## 5. Proof (when building)

- Pytest: profiles shape presentation; due/SRS unchanged; no second due engine; Studio/API path.
- Studio: Environment panel wired to `/api/education/environment/*`.
- Live: notes/marathon-card248-live-smoke.json.
