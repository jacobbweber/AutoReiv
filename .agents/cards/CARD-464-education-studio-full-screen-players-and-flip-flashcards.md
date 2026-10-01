---
id: CARD-464
title: "Education Studio expansion: full-screen players and flip-style flashcards"
status: Done
completed: 2026-10-01
created: 2026-09-24
branch: qa
adr: ADR-0059 (Education Studio = operator + players)
related:
  - CARD-463
  - CARD-448
  - CARD-447
labels:
  - type:feature
  - area:education
  - area:frontend
  - P2
needs_decision: none
milestone: M23
---

# [CARD-464] Education Studio expansion: full-screen players and flip-style flashcards

> **Status**: Done (merged into qa 2026-10-01)
> **Created**: 2026-09-24
> **Observed during**: Jacob review of Education Studio on Jarvis - after the legacy panels go (CARD-463), the players should own the screen and flashcards should look like real cards.
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)
> **Labels**: `type:feature`, `area:education`, `area:frontend`, `P2`
> **Related**: [CARD-463](./CARD-463-education-studio-remove-legacy-learning-os-panels.md) (predecessor), [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md) (players, Done), [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md) (operator bar, Done)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine layout - **still no product code** |
| **`build`** | Implement the full-screen players and flip cards |
| **`merge to qa`** | After In Review + the Human Verification Runbook passes on Jarvis |

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-463](./CARD-463-education-studio-remove-legacy-learning-os-panels.md) (frees the space) |
| **Blocked by** | CARD-463 merge |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Flashcards should look and feel like real cards: a card you flip over to see the answer.
2. With the old panels gone, the flashcard / quiz / test players and my progress should fill most of the screen instead of sitting in a thin strip.

### Beat 2: What AutoReiv does now

1. `#educationPlayersConsole` (`index.html` ~L3273, CARD-448) is a `flex-shrink-0` strip under the operator bar; the legacy panels (removed by CARD-463) take the rest of the height.
2. Flashcard player: `#educationPlayerFlashFront` and `#educationPlayerFlashBack` are two stacked boxes (`min-h-[3rem]` / `min-h-[2.5rem]`, `text-xs`); **Reveal back** (`#educationPlayerFlashRevealBtn`) un-hides the back below the front; then Know / Miss (`#educationPlayerFlashKnowBtn`, `#educationPlayerFlashMissBtn`).
3. Quiz and Test players use small `text-xs` prompt boxes (`min-h-[3rem]`) and a one-line answer input.
4. Progress lives in the operator bar's small inline panel `#educationOperatorProgressPanel` (CARD-447), toggled by the Progress button.
5. Logic lives in `education_players.js` (716 lines) and `education_operator.js`; tests `card_448_education_studio_players.test.js`, `card_447_education_studio_operator.test.js`.

### Beat 3: What will change

1. **Layout:** under the compact operator bar, the players area becomes the main `flex-1` region (full width and height, scrolls on small screens). Mode buttons (Flashcard / Quiz / Test / **Progress**) act as tabs for that region.
2. **Flip flashcards:** one large card centred in the region. Click the card or press **Space** to flip (CSS 3D rotate, front = question, back = answer). Know / Miss appear after the flip. Respect `prefers-reduced-motion` (instant swap instead of animation). Deck position (e.g. "3 / 12") shown above the card.
3. **Quiz / Test:** larger prompt text and a multi-line answer box; result shown beneath; Test summary uses the space.
4. **Progress:** the Progress tab shows the same data as today's operator Progress panel, rendered in the big region. The operator bar Progress button opens that tab (one progress view, not two).
5. Keep existing element ids where the behaviour is the same (`educationPlayerFlashFront`, `educationPlayerFlashBack`, grade buttons, quiz / test ids) so CARD-448 tests keep working; the Reveal button becomes the flip control.
6. No backend or API changes; same endpoints and durable grading.

### Beat 4: What dies today

1. The stacked front / back boxes and the separate **Reveal back** label (replaced by the flip card).
2. The `flex-shrink-0` thin-strip layout of `#educationPlayersConsole`.
3. The small inline `#educationOperatorProgressPanel` body in the operator bar (progress renders in the Progress tab instead).
4. Fixed `min-h-[3rem]` / `text-xs` prompt sizing in the three players.

---

## 2. Acceptance criteria (EARS)

- **[REQ-464-001]** WHILE Education Studio is open, THE players region SHALL fill the space below the operator bar.
- **[REQ-464-002]** WHEN Jacob clicks the flashcard or presses Space, THE SYSTEM SHALL flip it to show the answer, and SHALL show Know / Miss only after the flip.
- **[REQ-464-003]** WHERE the OS requests reduced motion, THE SYSTEM SHALL swap card sides without animation.
- **[REQ-464-004]** WHEN Jacob grades a card, THE SYSTEM SHALL record the grade through the existing Learning OS endpoint exactly as today.
- **[REQ-464-005]** WHEN Jacob clicks Progress (tab or operator button), THE SYSTEM SHALL show progress in the main region, and THE SYSTEM SHALL NOT render a second progress view in the operator bar.
- **[REQ-464-006]** THE Quiz and Test players SHALL use the enlarged prompt and a multi-line answer box, with the same grading behaviour.

### Tests (write first at build)

1. Flashcard: flip toggles a `flipped` state; grade buttons hidden before flip, visible after; Space key flips.
2. Reduced motion: no transition class when `matchMedia('(prefers-reduced-motion: reduce)')` matches.
3. Progress: operator Progress button activates the Progress tab; no inline progress body in the operator bar.
4. Existing CARD-448 grading tests still pass unchanged.

---

## 3. Human Verification Runbook (under 2 minutes)

1. Pull qa, restart with the serve-hygiene skill, hard-refresh.
2. Education Studio -> set a topic with due cards -> **Flashcard** -> **Start deck**. Expected: one large card fills the area.
3. Click the card (or press Space): it flips to the answer; Know / Miss appear. Click **Know**: the next card appears.
4. **Quiz** -> Start / Next: large prompt, multi-line answer; Grade shows a result.
5. Click **Progress** in the operator bar: progress fills the main area.

**Failure signals:** a thin strip with empty space below; the answer visible before flipping; the grade not saved (Due count unchanged after Know).

---

## 4. Constraints

- Docs-only until **build**.
- Build only after CARD-463 is merged.
- No backend changes.
- No `main` merge, no GitHub PR, no version bump for docs-only.

---

## 5. Reply phrases

- Refine layout: say **continue**.
- Start implementation: say **build**.
- After the runbook passes: say **merge to qa**.

## Decision (Jacob, 2026-09-30)
- Approved the class-b recommendation: **full-screen players** (Flashcard / Quiz / Test take the space CARD-463 frees) and **flip-style flashcards** (front -> tap/click/Space flips -> grade).
- Build after CARD-463; CARD-435 is updated to follow. UI/product card: live-check with screenshots, leave **In Review** for Jacob's **merge to qa**.

## Log
- 2026-09-30: Jacob approved (class-b): full-screen players + flip flashcards, after CARD-463. Not started yet.

## Outcome (2026-10-01, In Review)
- **Branch:** `card/464-education-full-screen-players`, cut from `card/463-education-remove-legacy-panels`. Its diff on top of 463 is this card only. Merging 464 brings 463 with it.
- **Layout (REQ-464-001):** `#educationPlayersConsole` is the `flex-1` region under the operator bar. Mode buttons are larger tabs: Flashcards / Quiz / Test / **Progress**. Each player panel grows to fill the region, and the region scrolls when the window is small.
- **Flip flashcards (REQ-464-002/003):** `#educationPlayerFlashCard` is one large focusable card. `#educationPlayerFlashFront` and `#educationPlayerFlashBack` are its two faces (CSS 3D `rotateY`, `studios.css` `.edu-flip-*`). Click the card, press Space (Flashcards tab, focus not in a text field or on a button) or use **Flip card** (the old Reveal button, same id). The answer text is only written on the first flip. Know / Miss appear after it, and the card can be turned back and forth. Under reduced motion the card has no `edu-flip-animated` class and the sides swap instantly (also a CSS media query). The deck position is shown above the card.
- **Grading (REQ-464-004):** unchanged. `POST /api/education/quiz/grade` runs once per Know / Miss, and the next card starts face down.
- **Progress (REQ-464-005):** the operator's progress view (`#educationOperatorProgressPanel` and the same body / Refresh ids) moved into the players' Progress tab. The operator bar has no inline progress body and no Hide button any more. The operator Progress button and the Progress tab both open that tab and load `/api/education/progress`.
- **Quiz / Test (REQ-464-006):** larger prompts (`text-base`/`text-lg`, `min-h-[8rem]`) and multi-line `<textarea>` answers with the same ids; grading is unchanged.
- **Code:** `education_players.js` adds `flipFlashcard`, `shouldFlipOnKey`, `prefersReducedMotion`, `getPlayerMode` and the `progress` mode; `education_operator.js` drops the Hide wiring. No backend change.
- **Tests:** `card_464_education_players_full_screen_flip.test.js` (10 tests: flip state, answer hidden before the flip, grade once then the next card face down, reduced motion, Space rules, Progress tab, layout). The CARD-448 / 447 tests pass unchanged. Vitest: 150 files / 936 tests.
- **Live check (throwaway clone serve on :8770, three seeded Raft cards, desktop 1400x900 + phone 390x844):**
  - Start deck shows card 1/3 face up with the back empty and Know / Miss hidden.
  - Clicking the card flips it: back text shown, grade row visible, animated.
  - Know sent 1 grade POST for the right item; the status read "Pass (durable). Next due ..." and the next card came up face down.
  - Space flips it.
  - The quiz answer box is a textarea.
  - The operator Progress button opened the Progress tab; nothing renders in the operator bar.
  - Reduced motion: the card flips with no animation class and `transition-duration: 0s`.
  - 0 console errors.
- **Screenshots:** `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui0930\464-flashcard-front-desktop.png`, `464-flashcard-front-phone.png`, `464-flashcard-flipped-desktop.png`, `464-flashcard-flipped-phone.png`, `464-quiz-desktop.png`, `464-quiz-phone.png`, `464-progress-desktop.png`, `464-progress-phone.png`.
- 2026-10-01: Built (stacked on CARD-463); live-checked on :8770 with screenshots; In Review for Jacob's **merge to qa**.
- 2026-10-01 (v2, Jacob review of the flipped screenshot): in the default-size window Know / Miss were pushed below the card. Now the flashcard panel takes exactly the space left (`min-h-0`), the header, meta and grade rows don't shrink, and only the card (no fixed height, min 6rem) shrinks or grows. The grade caption moved to a tooltip. Live check on :8770: Flip / Know / Miss are on screen with no scrolling (players and view scroll 0/0) at the default desktop window (card 700x148), on phone 390x844 (card 344x257) and in the maximized window (card 896x450, which uses the full height). Screenshots: `C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui0930\464-flashcard-flipped-desktop-v2.png`, `464-flashcard-flipped-phone-v2.png`, `464-flashcard-flipped-desktop-maximized-v2.png`. Still In Review.
