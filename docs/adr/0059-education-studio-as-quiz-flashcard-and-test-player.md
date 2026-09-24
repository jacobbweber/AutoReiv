# ADR-0059: Education Studio as quiz flashcard and test player

> **Date**: 2026-09-23  
> **Status**: Accepted  
> **Accepted**: 2026-09-23 (Jacob product lock: do **not** remove Education Studio; repurpose it)  
> **Deciders**: Jacob Weber, coding assistant  
> **Consulted**: CARD-435 Tutor-first direction; CARD-438 durable chat grading; live Education Studio panels  
> **Related Cards**: [CARD-435](../cards/CARD-435-education-tutor-first-direction.md), [CARD-438](../cards/CARD-438-chat-quiz-flashcard-turns-durable-grading.md), [CARD-442](../cards/CARD-442-retire-education-studio-landing.md) (Superseded), [CARD-446](../cards/CARD-446-education-studio-flashcard-quiz-test-players.md)  
> **Amends**: CARD-435 fork that said Education Studio landing **retires** (dated decision lock below). No prior ADR had locked Studio retirement.

---

## 1. Context & Problem Statement

CARD-435 locked a Tutor-first Learning OS north star and scaffolded [CARD-442](../cards/CARD-442-retire-education-studio-landing.md) to **retire** the Education Studio landing/bottom-nav panel farm after Tutor+Wiki covered the program. CARD-436..438 shipped Study entry and durable chat quiz/flashcard grading while Studio stayed as reference.

Jacob's product lock (2026-09-23):

> We will NOT remove Education Studio. We will repurpose it to a flash card, quiz, and test player.

The retirement end-state in CARD-442 therefore dies. AutoReiv still needs a clear boundary: Tutor owns coaching + durable Learning OS grading; Studio becomes the dedicated **interactive player** surface (not a competing Study destination and not a vestigial dashboard to delete).

---

## 2. Decision Drivers

* Keep a dedicated interactive surface for flashcards, quizzes, and tests (deck/player UX), not only chat turns.
* Preserve Tutor-first Learning OS skills, durable ledger grades, and Study entry (CARD-436..441 remain valid).
* Avoid silent contradiction with CARD-435 / CARD-442 retirement language.
* Do not revive CARD-434 monolith-split-as-first-build theatre; player work is a focused repurpose card.
* Lumina stays separate.

---

## 3. Considered Options

* **Option 1**: Keep CARD-442 — hide/remove `#tab-education` / `#view-education` after Tutor+Wiki cover the program.
* **Option 2**: Leave Studio as the multi-panel Learning OS dashboard forever (Tutor chat grading is optional theatre).
* **Option 3**: **Cancel Studio retirement.** Repurpose Education Studio as the flashcard + quiz + test **player** UI. Tutor/chat Learning OS keeps coaching + durable grading. Supersede CARD-442; scaffold a build-last player card.

---

## 4. Decision Outcome

Chosen option: **Option 3**.

### Decision lock (2026-09-23)

1. **Education Studio stays.** It is **not** retired and is **not** vestigial chrome to delete.
2. **Education Studio role** = interactive **player** for flashcards, quizzes, and tests (deck/session player UX on `#view-education` / Education tab).
3. **Tutor education mode / Study** remains the coaching + Learning OS skill entry; durable grades stay on Learning OS APIs / agent tools (CARD-438 path).
4. **CARD-442** is **Superseded**. "Retire Education Studio landing" is no longer the end state of the Tutor-first wave.
5. **CARD-446** implements the player repurpose and builds **last** after Tutor Learning OS due/wiki/progress cards that still make sense (439, 440, 441) are Done or In Review as appropriate.
6. **CARD-444 / CARD-445** stay valid Ready work (skill efficiency / turn budget); they do not assume Studio death.
7. **CARD-434** remains Superseded (monolith split is still the wrong first build); player work does not reopen 434.

### Positive Consequences

* Clear product split: Tutor coaches and grades; Studio plays interactive decks/tests.
* Operators keep a focused player surface without losing Tutor-first Study entry.
* Governance matches Jacob's lock; retirement no longer competes with player intent.

### Negative Consequences / Trade-offs

* Education tab / `#educationStudio` remains in IA; nav cleanup from CARD-442 does not ship.
* Player UX must still call the same durable Learning OS grade paths (no ephemeral Studio-only scores).
* Older CARD-435 prose that said "Studio retires" must be amended in-place (this ADR + card edits); readers should prefer this lock over pre-2026-09-23 retirement sentences.

---

## 5. Pros and Cons of Options

### Option 1 (retire Studio)
* Good, because IA shrinks to Study/Tutor + Wiki.
* Bad, because it removes the natural home for interactive deck/test players Jacob wants.

### Option 2 (Studio stays as dashboard farm)
* Good, because no nav change.
* Bad, because it fights Tutor-first Learning OS and keeps panel-farm gravity.

### Option 3 (Studio = player; Tutor = coach/grader)
* Good, because matches Jacob's lock and keeps durable Tutor rails.
* Bad, because Studio frontend still needs a focused player rebuild (CARD-446) instead of a delete.

---

## 6. Follow-up

* Supersede [CARD-442](../cards/CARD-442-retire-education-studio-landing.md).
* Amend [CARD-435](../cards/CARD-435-education-tutor-first-direction.md) forks and successor table.
* Implement players on [CARD-446](../cards/CARD-446-education-studio-flashcard-quiz-test-players.md) **last**.
