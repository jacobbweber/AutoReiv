---
id: CARD-439
title: "Due Reviews in Tutor Education Mode (SRS / Retention from Study)"
status: Done
created: 2026-09-23
adr: none
labels:
  - type:feature
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-439] Due Reviews in Tutor Education Mode (SRS / Retention from Study)

> **Status**: Done
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **4 of 7**.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine due queue UX, retention vs quiz-next split — **still no product code** |
| **`build`** | Implement due review surface + complete path in Tutor education mode / Study |
| **`merge to qa`** | After In Review + live operator proof |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md); [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) for durable grade path on review answers |
| **Blocked by** | No education-mode entry; no durable grade write |
| **Unlocks** | [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) due summary; feeds Studio players on [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) ([CARD-442](./CARD-442-retire-education-studio-landing.md) Superseded) |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Due SRS / retention work must be **surfaceable and completable from Tutor education mode / Study**, not only from Education Studio quiz panels.
2. Completing a due review must update durable Learning OS state (same anti-theatre bar as CARD-438).

### Beat 2: What AutoReiv does now

1. Due mastery: `GET /api/education/mastery/due`; quiz next: `GET /api/education/quiz/next`; retention routine: `POST /api/education/retention/run` (`src/application/education/retention_routine.py`, `srs.py`).
2. Education Studio surfaces due/SRS beside Ask/quiz chrome; delivery profiles explicitly must not replace ledger/SRS (`education.js` environment copy).
3. Tutor education mode (CARD-437) and chat grading (CARD-438) are the intended home; without this card, due work may remain Studio-panel-centric.

### Beat 3: What will change

1. In Tutor education mode / Study, operator can **list due reviews** and **run/complete** them via named Learning OS review skill(s) from CARD-436.
2. Completion writes durable grade/SRS updates (reuse CARD-438 write path + retention/mastery APIs as inventory directs).
3. Empty due queue is an honest empty state, not fake items.
4. Education Studio due/quiz panels remain; player repurpose is CARD-446 (Studio not retired).

**Out of scope:** Wiki curation ([CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md)); full progress dashboard ([CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md)); Studio players ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)); changing delivery-profile semantics that replace SRS (forbidden).

### Beat 4: What dies today

1. “Due reviews only live in Education Studio panels” as the product path.
2. Fake due lists that do not match `/api/education/mastery/due` or documented Learning OS due source.

---

## 2. Acceptance criteria

- **[REQ-439-001]** WHEN the operator opens due reviews from Tutor education mode / Study, THE SYSTEM SHALL show items sourced from Learning OS due APIs (`/api/education/mastery/due` and/or inventory-locked equivalent), not a client-only list.
- **[REQ-439-002]** WHEN the learner completes a due review turn, THE SYSTEM SHALL persist durable grade/SRS state and the item SHALL leave or reschedule on the due list accordingly after refresh.
- **[REQ-439-003]** WHEN nothing is due, THE SYSTEM SHALL show an explicit empty state.
- **[REQ-439-004]** THE SYSTEM SHALL NOT claim delivery profiles replace ledger/SRS.

---

## 3. Proof / live-test notes

1. Seed or use a topic with known due items via mastery/quiz APIs; open Study → Tutor → due reviews; complete one.
2. Re-fetch due API; confirm schedule/grade changed; hard-refresh Tutor view.
3. Clear dues; confirm empty state.
4. Failure modes: retention/run or grade failure → operator-visible error; no silent success.
5. Automated: contract test due list + complete + due list delta.

---

## 4. Constraints

- Branch: `feat/card-439-*` from `qa` after **build**.
- **No product code** until **build**.
- No `main` merge, no GitHub PRs, no version bump for docs-only.

---



---

## Implementation notes (In Review)

**Branch**: `feat/card-439-due-reviews-in-tutor-education-mode`

### Chosen path (locked at build)

| Surface | Mechanism | Durable twin |
|---|---|---|
| Tutor education-mode **Due reviews** button | `#chatEducationModeDueBtn` + `#chatEducationModeDuePanel` in Study strip (`study_entry.js`) | `GET /api/education/mastery/due` |
| Skill `due-review` | Tools `education_due_review_list`, `education_due_review_complete`, `education_retention_run`, plus grade twins | mastery due + `POST /api/education/quiz/grade` + `POST /api/education/retention/run` |

- Empty due queue → `empty=true` / `empty_state="No due reviews."` (no fake items).
- Complete uses CARD-438 quiz-grade write path; reports `left_due_queue` / `still_due`.
- Retention without orchestrator → honest failure (`no_orchestrator`); never invents job ids.
- Delivery profiles must not replace ledger/SRS (tool copy + Study panel caption).
- Education Studio `#educationDueList` / retention buttons **kept** (ADR-0059; players = CARD-446).

### Delivered

- `src/application/skills/education_tools.py` (due list/complete + retention run)
- `platform-packs/tutor/pack.json` + `skills/due-review/SKILL.md`
- `src/web/static/modules/studios/study_entry.js` + `index.html` education-mode due chrome
- Inventory agent-tools column for `due-review`
- Tests: `tests/unit/education/test_card439_due_reviews_in_tutor_education_mode.py`
- Frontend: `tests/unit/frontend/card_439_due_reviews.test.js`

### Live-test checklist (Jacob / Jarvis)

1. Restart serve on tip; Ctrl+F5 Control Plane.
2. **Study** → topic → Tutor education mode strip visible.
3. Click **Due reviews** on the strip → panel lists items from `GET /api/education/mastery/due?agent_id=tutor` (or **No due reviews.**).
4. Seed a due item if empty (Studio quiz grade miss, or mastery upsert + past `next_due`); Refresh; confirm list matches API.
5. In Tutor chat (skill `due-review`), complete one item via `education_due_review_complete`; re-fetch due API — item left or rescheduled.
6. Force grade failure (unknown `item_id`) — Tutor must not claim durable success.
7. Education tab — Studio `#educationDueList` / Run retention still present.
8. Automated: `pytest tests/unit/education/test_card439_due_reviews_in_tutor_education_mode.py -q` and vitest `card_439_due_reviews.test.js`.

### Live proof result / merge note

- **2026-09-23 (ET)**: Live proof accepted; **merge to qa** completed (merge tip `808d998f`).
- **Status**: Done.
- Next Ready in Tutor Learning OS order: **CARD-440** (wiki curation), then CARD-441; CARD-446 remains last.

### After live proof

Say **merge to qa**.


## 5. Reply phrases

- Refine due UX: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
