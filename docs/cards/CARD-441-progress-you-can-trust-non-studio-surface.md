---
id: CARD-441
title: "Progress You Can Trust (Non-Studio Surface: Tutor Cards and/or Wiki Views)"
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

# [CARD-441] Progress You Can Trust (Non-Studio Surface: Tutor Cards and/or Wiki Views)

> **Status**: In Review
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **6 of 7** (last Tutor/Wiki progress capability before Studio **player** card CARD-446).

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine Tutor cards vs Wiki views, which mastery fields show — **still no product code** |
| **`build`** | Implement non-Studio course/mastery/due progress surface |
| **`merge to qa`** | After In Review + live operator proof |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md); [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md); [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md); [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md) preferred so library and grades feed progress |
| **Blocked by** | Progress that only exists inside `#educationCourseChrome` / Education Studio panels |
| **Unlocks** | [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) can assume progress exists outside Studio panels; [CARD-442](./CARD-442-retire-education-studio-landing.md) Superseded |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Course list, mastery, and due summary must be visible **without Education Studio panels** — Tutor cards and/or Wiki views.
2. Progress must be **trustable**: same durable Learning OS sources as grades/reviews, not a decorative bar.

### Beat 2: What AutoReiv does now

1. Course/mastery chrome is concentrated in Education Studio: `#educationCourseChrome`, mastery badge/progress bar, course steps in `src/web/templates/index.html`, rendered by `renderEducationCourseChrome` in `education.js`.
2. APIs: `GET /api/education/course`, `GET /api/education/mastery`, `GET /api/education/mastery/due`, `GET /api/education/course/depth`, learner `GET /api/education/learner`, portfolio `POST /api/education/course/portfolio/create`.
3. After CARD-437..440, Tutor can study, grade, review, and curate — but without this card, the operator may still need Education Studio to *see* program progress.

### Beat 3: What will change

1. Add operator-visible progress on **non-Studio** surface(s): Tutor education-mode cards and/or Wiki views (exact mix locked at **continue**/**build**).
2. Surface at least: course list or active course, mastery summary, due summary — all read from Learning OS APIs above (or inventory-locked successors).
3. After a CARD-438 grade or CARD-439 review, this surface updates after refresh without opening Education Studio.
4. Keep Studio chrome (Studio stays as player per ADR-0059); do not make Studio the only progress UI.

**Out of scope:** Studio player rebuild ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)); fake animated progress unrelated to ledger; Lumina.

### Beat 4: What dies today

1. “You can only trust progress if you open Education Studio.”
2. Progress UI that does not round-trip to Learning OS stores.

---

## 2. Acceptance criteria

- **[REQ-441-001]** WHEN the operator views education progress from Tutor cards and/or Wiki views (documented path), THE SYSTEM SHALL show course and mastery/due summary sourced from Learning OS APIs without requiring `#view-education`.
- **[REQ-441-002]** WHEN a durable grade or due completion lands (CARD-438/439), THEN after refresh THE non-Studio progress surface SHALL reflect the change.
- **[REQ-441-003]** WHEN APIs fail, THE SYSTEM SHALL show failure/empty honestly — no fabricated mastery percentages.
- **[REQ-441-004]** THE SYSTEM SHALL NOT remove Education Studio progress chrome on this card (Studio stays; player work is CARD-446).

---

## 3. Proof / live-test notes

1. Complete a graded turn and a due review; open only Tutor/Wiki progress surface (do not open Education Studio); confirm numbers match API payloads.
2. Hard-refresh; still matches.
3. Stop education API or force 500; confirm error/empty, not stale fake 100%.
4. Automated: test progress helper/API consumer against mastery/course fixtures.

---

## 4. Constraints

- Branch: `feat/card-441-*` from `qa` after **build**.
- **No product code** until **build**.
- No `main` merge, no GitHub PRs, no version bump for docs-only.

---

## 5. Reply phrases

- Refine progress surface: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
