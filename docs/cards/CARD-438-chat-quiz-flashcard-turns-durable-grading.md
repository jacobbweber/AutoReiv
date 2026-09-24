---
id: CARD-438
title: "Chat Quiz / Flashcard Turns + Durable Grading (Learning OS Ledger)"
status: In Review
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

> **Status**: In Review
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



---

## Implementation notes (In Review)

**Branch**: `feat/card-438-chat-quiz-flashcard-durable-grading`

### Chosen write path (locked at build)

Agent-callable tools in `src/application/skills/education_tools.py` call application-layer `quiz_engine` + `education_mastery` ops (same durable ledger as HTTP):

| Skill | Tools | Durable twin |
|---|---|---|
| `quiz-turn` | `education_quiz_extract`, `education_quiz_next`, `education_quiz_grade` | `/api/education/quiz/extract|next|grade` |
| `flashcard-turn` | `education_flashcard_next`, `education_flashcard_grade`, `education_mastery_due`, `education_mastery_upsert` | mastery due/upsert + **shared** `POST /api/education/quiz/grade` |

- Registered on master tool registry in `src/infrastructure/agents/registry.py` (alongside Wiki tools).
- Tutor `pack.json` `pack_tool_names` + skill `tools` lists name the exact tools; SKILL.md bodies document turn shape.
- Grade failure → `{success: false, durable: false, error: ...}` — never a fake pass.
- Education Studio `#educationQuizPanel` / `/api/education/quiz/grade` UI **kept** (REQ-438-004).

### Delivered

- `src/application/skills/education_tools.py`
- Registry bootstrap wiring
- `platform-packs/tutor/pack.json` + `skills/quiz-turn/SKILL.md` + `skills/flashcard-turn/SKILL.md`
- Inventory agent-tools columns updated (`docs/education/tutor-learning-os-inventory.md`)
- Tests: `tests/unit/education/test_card438_chat_quiz_flashcard_durable_grading.py`
- Out of scope held: CARD-439 due reviews UX, 440 wiki curation, 441 progress surface, 442 Studio retire, Lumina

### Live-test checklist (Jacob / Jarvis)

1. Cold browser on Jarvis Control Plane; restart serve if needed so Tutor pack + education tools re-bootstrap.
2. **Study** → topic (e.g. one with Priming/Quiz Wiki notes) → Tutor education mode strip shows `start-resume-topic`.
3. In Tutor chat, run a **quiz-turn**: ask Tutor to quiz you / invoke Learning OS skill `quiz-turn`. Confirm tool calls include `education_quiz_next` or `education_quiz_extract`, then after your answer `education_quiz_grade`. Capture `item_id`.
4. Inspect durable state: `GET /api/education/mastery?agent_id=tutor` (and/or `/api/education/quiz/next?agent_id=tutor`) — graded item shows `grade` / `next_due` / counts.
5. Run a **flashcard-turn**: Tutor calls `education_flashcard_next` then `education_flashcard_grade`; confirm same ledger updated.
6. **Hard-refresh** browser; re-check mastery/due/next — progress still present without opening Education Studio.
7. Force failure: grade unknown `item_id` or empty expected (via tool / API) — Tutor must **not** claim durable success.
8. Open **Education** tab — Studio quiz panel still works (`#educationQuizPanel`).
9. Automated: `pytest tests/unit/education/test_card438_chat_quiz_flashcard_durable_grading.py -q`

### After live proof

Say **merge to qa**.


## 5. Reply phrases

- Refine turn contract: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
