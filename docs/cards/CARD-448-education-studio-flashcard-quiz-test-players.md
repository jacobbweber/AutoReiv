---
id: CARD-448
title: "Education Studio Flashcard / Quiz / Test Players (Interactive Decks)"
status: In Review
created: 2026-09-23
adr: ADR-0059
labels:
  - type:feature
  - area:education
  - area:frontend
  - P0
parent: CARD-446
---

# [CARD-448] Education Studio Flashcard / Quiz / Test Players (Interactive Decks)

> **Status**: In Review
> **Created**: 2026-09-23
> **Baseline**: `qa` after CARD-441 Done + ADR-0059 operator+players amendment
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)
> **Labels**: `type:feature`, `area:education`, `area:frontend`, `P0`
> **Parent**: [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)
> **Build order**: **2 of 2** Studio implementation slices — **after** [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md)
> **Prior scope note**: Interactive players were previously the whole of CARD-446; CARD-446 is now the parent program. This card owns players only.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine player UX (flashcard vs quiz vs test), deck session shape — **still no product code** |
| **`build`** | Only after CARD-447 Done or In Review with proof (operator console + Tutor context exist); then build Studio players |
| **`merge to qa`** | After In Review + live operator proof on Jarvis Education tab players |

Do **not** write product code until Jacob says **`build`** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on (hard)** | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) **Done** (durable grade/ledger path); [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md) **Done** or **In Review with proof** so Studio operator context exists before player polish |
| **Blocked by** | Attempting player theatre with ephemeral-only scores; starting before Studio operator/context proof on CARD-447 |
| **Related** | [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md), [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) stay Tutor-side; [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md) / [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) ledger feeds |
| **Unlocks** | Education Studio interactive deck/test play on the operator console (ADR-0059); Tutor remains coach + durable grader |

**Explicit:** Build **after** CARD-447. Studio is **kept** as operator+players, not retired ([ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)).

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Education Studio hosts interactive **flashcard, quiz, and test players** — deck/session UX, not only static panels or chat turns.
2. Players sit on the Studio **operator console** (topic/course already saved via CARD-447); Tutor remains coach.
3. Players must feel like real deck play (advance card, answer, see grade, next) on the Education tab.
4. Grades must hit the same Learning OS ledger paths as Tutor tools (CARD-438 family).

### Beat 2: What AutoReiv does now

1. `#tab-education` / `#view-education` / `#educationStudio` still present; `education.js` owns Ask, course chrome, quiz/SRS panels, labs, amplifiers (panel farm, not a focused player).
2. Durable grading exists for chat via CARD-438 agent tools + `/api/education/quiz/grade` / mastery APIs; Studio quiz helpers still exist as reference.
3. CARD-447 (when Done) owns operator strip relocation + Tutor context; until then Studio is still engineering-heavy for players.
4. CARD-442 retirement remains Superseded. Lumina remains separate.

### Beat 3: What will change

1. Refocus Education Studio UX into **three player modes**: flashcard player, quiz player, and test player (interactive deck/session chrome on `#view-education`).
2. Each player session reads/writes the **same durable Learning OS** paths Tutor uses (quiz grade / mastery due/upsert / documented equivalents) — no ephemeral-only Studio scores.
3. Prefer Studio-active topic/course from CARD-447 as the session context for decks/tests.
4. Keep Study / Tutor education mode as the coaching entry; Studio player is complementary, not a second Study destination that bypasses Learning OS rails.
5. Prune or demote non-player panel-farm chrome only as needed to make players honest; this is **not** CARD-434 monolith-split-as-success and **not** a nav retirement.

**Out of scope:** Relocating Due/Progress/Wiki curate ([CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md)); retiring/hiding `#tab-education`; Lumina; CARD-434 submodule decomposition as the goal; Tutor skill efficiency ([CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md)); turn-budget defaults ([CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md)); merging to main; version bump solely for docs.

### Beat 4: What dies today

1. Treating Education Studio as disposable vestigial chrome once Tutor covers chat turns.
2. Player UX that shows grades without Learning OS ledger writes.
3. Building players before Studio operator/context exists (skipping CARD-447).

---

## 2. Acceptance criteria

- **[REQ-448-001]** WHEN Jacob says **`build`** and CARD-447 is Done or In Review with proof, THE SYSTEM SHALL provide Education Studio **flashcard**, **quiz**, and **test** player surfaces on `#view-education` (or documented Education tab equivalent).
- **[REQ-448-002]** WHEN the learner completes an item in a Studio player, THE SYSTEM SHALL persist durable grade/progress via Learning OS APIs (same family as CARD-438: quiz grade and/or mastery upsert/course mastery grade).
- **[REQ-448-003]** WHEN the browser hard-refreshes after a player session, THE OPERATOR PATH SHALL still see that progress in mastery/due/next (or documented equivalent) without relying on in-memory panel state.
- **[REQ-448-004]** WHEN Studio has an active topic/course (CARD-447), player sessions SHALL use that context (or document an explicit override path).
- **[REQ-448-005]** THE SYSTEM SHALL NOT remove the Education Studio tab/landing as success criteria for this card (Studio stays per ADR-0059).
- **[REQ-448-006]** THE SYSTEM SHALL NOT treat splitting `education.js` into `education/*` submodules as success criteria (CARD-434 stays Superseded).
- **[REQ-448-007]** Lumina Studio SHALL remain available (not retired or coupled by this card).

---

## 3. Proof / live-test notes

1. Pre-flight: CARD-447 Done or In Review with proof; CARD-438 Done.
2. Open Education tab — flashcard player: run a short deck; confirm durable mastery/due change; hard-refresh.
3. Quiz player: answer graded item; confirm `/api/education/quiz/grade` or mastery path wrote; hard-refresh.
4. Test player: multi-item session completes with durable results (exact shape locked at **`build`**).
5. Confirm Study / Tutor education mode still works with Studio context; confirm Lumina still opens.
6. Failure modes: grade API failure surfaces; no fake success in player chrome.
7. Automated: contract tests for player grade write + refresh-visible ledger; nav still exposes Education tab.

---

## 4. Constraints

- Branch: `feat/card-448-*` from `qa` only after **`build`** and CARD-447 dependency proof.
- **No product code** until **`build`**.
- Do not implement [CARD-442](./CARD-442-retire-education-studio-landing.md) retirement.
- Do not implement [CARD-434](./CARD-434-education-studio-monolith-decomposition.md).
- No main merge, no GitHub PRs, no version bump for docs-only scaffolding.
- Plain full sentences; exact paths.

---

## 5. Reply phrases

- Refine player UX: say **`continue`**.
- Start implementation (only with CARD-447 proof): say **`build`**.
- After live proof: say **`merge to qa`**.
