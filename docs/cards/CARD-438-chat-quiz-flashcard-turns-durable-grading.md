---
id: CARD-438
title: "Chat Quiz / Flashcard Turns + Durable Grading (Learning OS Ledger)"
status: Ready
created: 2026-09-23
adr: none
labels:
  - type:feature
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-438] Chat Quiz / Flashcard Turns + Durable Grading (Learning OS Ledger)

> **Status**: Ready
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **3 of 7**.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine turn shapes, grade payload, flashcard vs quiz split — **still no product code** |
| **`build`** | Implement in-chat quiz/flashcard turns with durable Learning OS grading |
| **`merge to qa`** | After In Review + live operator proof |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md) (named quiz/flashcard skills); [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md) Done or In Review so Study → Tutor education mode exists |
| **Blocked by** | No Tutor education-mode entry; missing quiz grade APIs (should already exist) |
| **Unlocks** | [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md) (reviews reuse grade/ledger); [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Assessment happens as **Tutor chat turns** (quiz and flashcard), not only as Education Studio panel theatre.
2. Every grade must land in the **Learning OS ledger / mastery stores** so progress survives refresh and is operator-trustable.

### Beat 2: What AutoReiv does now

1. Quiz extract/grade/next: `POST /api/education/quiz/extract`, `POST /api/education/quiz/grade`, `GET /api/education/quiz/next` in `src/web/routers/education.py`; engines in `src/application/education/quiz_engine.py`, SRS helpers in `srs.py`.
2. Mastery ledger: `GET/POST /api/education/mastery`, `GET /api/education/mastery/due`, course mastery grade `POST /api/education/course/mastery/grade`.
3. Education Studio quiz UI in `education.js` / `#view-education` (local grade helpers `gradeEducationAnswerLocal` plus API grade path).
4. Wiki templates: `data/wiki/02_Resources/_Templates/education-quiz.md`, `education-flashcard.md`.
5. Tutor education mode Study entry (CARD-437) may exist before this card ships; without this card, chat still lacks first-class durable assessment turns.

### Beat 3: What will change

1. In Tutor education mode, named Learning OS skills drive **quiz turns** and **flashcard turns** in chat (prompt → learner answer → grade → next).
2. Grades **must** persist via Learning OS (`/api/education/quiz/grade` and/or course mastery grade / mastery upsert — exact write path locked at **build** from CARD-436 inventory). No ephemeral-only “looks graded in the bubble.”
3. Failure modes: grade API failure surfaces to operator; do not show fake success.
4. Keep Education Studio quiz panels working (reference); do not remove them here.

**Out of scope:** Due-review queue UX ([CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md)); wiki curation ([CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md)); non-Studio progress dashboard ([CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md)); Studio retirement ([CARD-442](./CARD-442-retire-education-studio-landing.md)).

### Beat 4: What dies today

1. Ephemeral quiz/flashcard theatre in Tutor chat (UI-only score with no ledger write).
2. The idea that durable grading only exists inside Education Studio panels.

---

## 2. Acceptance criteria

- **[REQ-438-001]** WHEN the learner completes a quiz or flashcard turn in Tutor education mode, THE SYSTEM SHALL persist a durable grade/progress record via Learning OS APIs (quiz grade and/or mastery upsert/course mastery grade).
- **[REQ-438-002]** WHEN the browser hard-refreshes after a graded turn, THE OPERATOR PATH SHALL still see that item reflected in mastery/due/next quiz data (`/api/education/mastery`, `/api/education/quiz/next`, or documented equivalent).
- **[REQ-438-003]** WHEN the grade API fails, THE SYSTEM SHALL NOT present a successful durable grade to the operator.
- **[REQ-438-004]** THE SYSTEM SHALL NOT remove Education Studio quiz UI on this card.

---

## 3. Proof / live-test notes

1. Study → Tutor education mode → run one quiz turn and one flashcard turn; capture item ids.
2. Call or inspect mastery/due/next APIs; confirm durable state changed.
3. Hard-refresh; confirm progress still present without Education Studio.
4. Force a grade failure (invalid payload or stopped service) and confirm error UX.
5. Automated: integration test that posts a chat/education-mode grade and asserts ledger row (path chosen at **build**).

---

## 4. Constraints

- Branch: `feat/card-438-*` from `qa` after **build**.
- **No product code** until **build**.
- No `main` merge, no GitHub PRs, no version bump for docs-only.
- Plain sentences; exact paths.

---

## 5. Reply phrases

- Refine turn contract: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
