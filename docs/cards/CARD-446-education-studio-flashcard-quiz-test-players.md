---
id: CARD-446
title: "Education Studio Flashcard / Quiz / Test Players (Interactive Decks; Build Last)"
status: Ready
created: 2026-09-23
adr: ADR-0059
labels:
  - type:feature
  - area:education
  - area:frontend
  - P0
parent: CARD-435
---

# [CARD-446] Education Studio Flashcard / Quiz / Test Players (Interactive Decks; Build Last)

> **Status**: Ready
> **Created**: 2026-09-23
> **Baseline**: qa after CARD-438 merge + ADR-0059 product lock
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)
> **Labels**: 	ype:feature, rea:education, rea:frontend, P0
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **LAST** after Tutor Learning OS cards **439 / 440 / 441** (and after **438** Done). Do **not** start before durable grading + due + progress paths are Done or In Review with proof as listed below.
> **Supersedes retirement intent of**: [CARD-442](./CARD-442-retire-education-studio-landing.md)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **continue** | Refine player UX (flashcard vs quiz vs test), deck session shape - **still no product code** |
| **uild** | Only after CARD-438 Done and CARD-439 / 440 / 441 Done or In Review with proof; then build Studio players |
| **merge to qa** | After In Review + live operator proof on Jarvis Education tab players |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on (hard)** | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) **Done** (durable grade/ledger path); [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md), [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md), [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) each **Done** or **In Review with proof** so coaching/due/library/progress exist before player polish |
| **Blocked by** | Attempting player theatre with ephemeral-only scores; starting before Tutor Learning OS due/progress proof |
| **Related** | [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md), [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) stay Tutor-side; do not block this card once 438/439/441 proof exists |
| **Unlocks** | Education Studio as the dedicated interactive player surface (ADR-0059); Tutor remains coach + durable grader |

**Explicit:** This card is **last** in the Tutor-first capability wave. Earlier cards capture Study/Tutor Learning OS. Studio is **kept** and **repurposed**, not retired ([ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)).

---

## 1. Four Beats

### Beat 1: What Jacob means

1. **Do not remove Education Studio.** Repurpose it into a **flashcard, quiz, and test player** — interactive decks/sessions, not just static panels.
2. Tutor / chat Learning OS still owns coaching + durable grading; Studio is the dedicated **player UI**.
3. Players must feel like real deck play (advance card, answer, see grade, next) on the Education tab.

### Beat 2: What AutoReiv does now

1. #tab-education / #view-education / #educationStudio still present; ducation.js owns Ask, course chrome, quiz/SRS panels, labs, amplifiers (panel farm, not a focused player).
2. Durable grading exists for chat via CARD-438 agent tools + /api/education/quiz/grade / mastery APIs; Studio quiz helpers (gradeEducationAnswerLocal + API path) still exist as reference.
3. CARD-442 previously planned to **retire** this landing after 436..441 — **cancelled** by ADR-0059 / this card.
4. Lumina remains a separate studio and is out of scope.

### Beat 3: What will change

1. Refocus Education Studio UX into **three player modes**: flashcard player, quiz player, and test player (interactive deck/session chrome on #view-education).
2. Each player session reads/writes the **same durable Learning OS** paths Tutor uses (quiz grade / mastery due/upsert / documented equivalents) — no ephemeral-only Studio scores.
3. Keep Study / Tutor education mode as the coaching entry; Studio player is complementary, not a second Study destination that bypasses Learning OS rails.
4. Prune or demote non-player panel-farm chrome only as needed to make players honest; this is **not** CARD-434 monolith-split-as-success and **not** a nav retirement.

**Out of scope:** Retiring/hiding #tab-education (superseded CARD-442); Lumina; CARD-434 submodule decomposition as the goal; Tutor skill efficiency ([CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md)); turn-budget defaults ([CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md)); merging to main; version bump solely for docs.

### Beat 4: What dies today

1. **"Retire Education Studio landing"** as the end state of CARD-442 / the CARD-435 retirement fork.
2. Treating Education Studio as disposable vestigial chrome once Tutor covers chat turns.
3. Player UX that shows grades without Learning OS ledger writes.

---

## 2. Acceptance criteria

- **[REQ-446-001]** WHEN Jacob says **build** and CARD-438 is Done and CARD-439/440/441 are Done or In Review with proof, THE SYSTEM SHALL provide Education Studio **flashcard**, **quiz**, and **test** player surfaces on #view-education (or documented Education tab equivalent).
- **[REQ-446-002]** WHEN the learner completes an item in a Studio player, THE SYSTEM SHALL persist durable grade/progress via Learning OS APIs (same family as CARD-438: quiz grade and/or mastery upsert/course mastery grade).
- **[REQ-446-003]** WHEN the browser hard-refreshes after a player session, THE OPERATOR PATH SHALL still see that progress in mastery/due/next (or documented equivalent) without relying on in-memory panel state.
- **[REQ-446-004]** THE SYSTEM SHALL NOT remove the Education Studio tab/landing as success criteria for this card (Studio stays per ADR-0059).
- **[REQ-446-005]** THE SYSTEM SHALL NOT treat splitting ducation.js into ducation/* submodules as success criteria (CARD-434 stays Superseded).
- **[REQ-446-006]** Lumina Studio SHALL remain available (not retired or coupled by this card).

---

## 3. Proof / live-test notes

1. Pre-flight: CARD-438 Done; CARD-439/440/441 Done or In Review with proof links before cutting eat/card-446-*.
2. Open Education tab — flashcard player: run a short deck; confirm durable mastery/due change; hard-refresh.
3. Quiz player: answer graded item; confirm /api/education/quiz/grade or mastery path wrote; hard-refresh.
4. Test player: multi-item session completes with durable results (exact shape locked at **build**).
5. Confirm Study / Tutor education mode still works; confirm Lumina still opens.
6. Failure modes: grade API failure surfaces; no fake success in player chrome.
7. Automated: contract tests for player grade write + refresh-visible ledger; nav still exposes Education tab.

---

## 4. Constraints

- Branch: eat/card-446-* from qa only after **build** and dependency proof.
- **No product code** until **build**.
- Do not implement [CARD-442](./CARD-442-retire-education-studio-landing.md) retirement.
- Do not implement [CARD-434](./CARD-434-education-studio-monolith-decomposition.md).
- No main merge, no GitHub PRs, no version bump for docs-only scaffolding.
- Plain full sentences; exact paths.

---

## 5. Reply phrases

- Refine player UX: say **continue**.
- Start implementation (only with 438 Done + 439/440/441 proof): say **build**.
- After live proof: say **merge to qa**.
