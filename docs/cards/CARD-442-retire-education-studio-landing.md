---
id: CARD-442
title: "Retire Education Studio Landing (Last; After Tutor+Wiki Cover the Program)"
status: Ready
created: 2026-09-23
adr: none
labels:
  - type:architecture
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-442] Retire Education Studio Landing (Last; After Tutor+Wiki Cover the Program)

> **Status**: Ready
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none (draft only if nav IA change needs a lasting ADR)
> **Labels**: `type:architecture`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **7 of 7 — LAST.** Do **not** start this card before CARD-436..441 are Done or In Review with proof.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine redirect targets, what dead code to delete vs hide — **still no product code** |
| **`build`** | Only after CARD-436..441 Done or In Review with proof; then remove/hide Education Studio landing |
| **`merge to qa`** | After In Review + live operator proof that Study/Tutor covers former Studio entry |

Do **not** write product code until Jacob says **build** on this card. Do **not** treat CARD-434 monolith split as this work.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on (hard)** | [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md), [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md), [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md), [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md), [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md), [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) — each **Done** or **In Review with proof** that Tutor+Wiki cover that slice |
| **Blocked by** | Any of CARD-436..441 still Ready without live proof; attempt to “just delete the tab” early |
| **Unlocks** | Clean IA: Study/Tutor education mode is the sole education entry; dead Studio landing gone |

**Explicit:** This card is **last**. Earlier cards exist to capture the education program and Tutor skills while Education Studio still exists as reference. Studio retirement must not precede that capture.

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Remove or hide the **bottom-nav Education Studio dashboard and panel farm** only after prior cards prove Tutor + Wiki cover the program.
2. Redirect any remaining Education entry to **Tutor education mode / Study**.
3. Goal is **retirement**, not monolith-splitting `src/web/static/modules/studios/education.js` ([CARD-434](./CARD-434-education-studio-monolith-decomposition.md) stays Superseded).

### Beat 2: What AutoReiv does now

1. `#tab-education` / `#view-education` / `#educationStudio` in `src/web/templates/index.html` still present; `initEducationStudio` in `education.js` still owns the panel farm.
2. After CARD-436..441 (when Done), Study → Tutor education mode, chat quiz/flashcards with durable grades, due reviews, wiki curation, and non-Studio progress exist — Studio is redundant as destination.
3. Lumina remains a separate studio and is **out of scope** for this retirement.

### Beat 3: What will change

1. Hide or remove bottom-nav / tab entry for Education Studio landing; remove or gut `#view-education` panel farm from operator IA.
2. Any bookmark/deep-link that still targets `data-studio="education"` / education tab **redirects** to Tutor education mode / Study (CARD-437 path).
3. Delete or quarantine dead Studio-only frontend that no longer has an operator path; keep shared Learning OS API clients if Tutor still imports them. Do **not** spend the card on a clean submodule split of the retired page.
4. Prove: cold operator can start/resume topic, quiz, due review, curate wiki, see progress — **without** Education Studio panels.

**Out of scope:** Lumina retirement or Lumina feature work; CARD-434-style `education/` submodule decomposition as the goal; merging to `main`; version bump solely for nav hide.

### Beat 4: What dies today

1. Education Studio as dashboard landing and bottom-nav destination.
2. Operator expectation that education means the multi-panel `#educationStudio` farm.
3. Any leftover plan to polish or monolith-split that landing as the Education first build.

---

## 2. Acceptance criteria

- **[REQ-442-001]** WHEN CARD-436..441 are Done or In Review with proof, and Jacob says **build**, THE SYSTEM SHALL remove or hide the Education Studio bottom-nav/tab landing (`#tab-education` / `#view-education` operator destination).
- **[REQ-442-002]** WHEN an operator hits a legacy Education Studio entry point, THE SYSTEM SHALL redirect to Tutor education mode / Study.
- **[REQ-442-003]** WHEN Education Studio landing is retired, THE OPERATOR SHALL still complete start/resume, quiz/flashcard grade, due review, wiki curation, and progress check via Tutor+Wiki paths without the panel farm.
- **[REQ-442-004]** THE SYSTEM SHALL NOT treat splitting `education.js` into `src/web/static/modules/studios/education/*` as success criteria for this card.
- **[REQ-442-005]** Lumina Studio SHALL remain available (not retired by this card).

---

## 3. Proof / live-test notes

1. Pre-flight checklist: links to CARD-436..441 proof notes / Done status before cutting `feat/card-442-*`.
2. After change: hard-refresh Jarvis UI — no Education Studio tab/landing; Study/Tutor education mode works end-to-end for the day-one reshape list from CARD-435.
3. Hit legacy URL/hash/tab id if any; confirm redirect.
4. Confirm Lumina still opens.
5. Failure modes: if a required Tutor path is missing, **stop** and reopen the owning CARD-436..441 rather than shipping a broken retirement.
6. Automated: nav/IA test that education tab is absent or redirects; smoke that Study entry still mounts.

---

## 4. Constraints

- Branch: `feat/card-442-*` from `qa` only after **build** and dependency proof.
- **No product code** until **build**.
- Do not implement [CARD-434](./CARD-434-education-studio-monolith-decomposition.md).
- No `main` merge, no GitHub PRs, no version bump for docs-only scaffolding.
- Plain full sentences; exact paths.

---

## 5. Reply phrases

- Refine retirement cut: say **continue**.
- Start implementation (only with 436..441 proof): say **build**.
- After live proof: say **merge to qa**.
