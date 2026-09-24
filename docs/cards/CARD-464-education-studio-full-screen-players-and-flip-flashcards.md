---
id: CARD-464
title: "Education Studio expansion: full-screen players and flip-style flashcards"
status: Ready
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
---

# [CARD-464] Education Studio expansion: full-screen players and flip-style flashcards

> **Status**: Ready
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

Do not write product code until Jacob says **build** on this card.

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
