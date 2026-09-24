# ADR-0059: Education Studio as operator surface and quiz / flashcard / test player

> **Date**: 2026-09-23  
> **Status**: Accepted  
> **Accepted**: 2026-09-23 (Jacob product lock: do **not** remove Education Studio; repurpose it)  
> **Amended**: 2026-09-23 (Jacob product lock: Studio = **operator + players**; Tutor = coach with Studio topic/course context; chat education-mode strip relocates into Studio)  
> **Deciders**: Jacob Weber, coding assistant  
> **Consulted**: CARD-435 Tutor-first direction; CARD-437..441 Tutor Learning OS APIs; live Education Studio panels; Projects Studio ↔ Developer active-project context parallel  
> **Related Cards**: [CARD-435](../cards/CARD-435-education-tutor-first-direction.md), [CARD-437](../cards/CARD-437-study-entry-tutor-education-mode-thin-shell.md), [CARD-438](../cards/CARD-438-chat-quiz-flashcard-turns-durable-grading.md), [CARD-439](../cards/CARD-439-due-reviews-in-tutor-education-mode.md), [CARD-440](../cards/CARD-440-wiki-curation-from-links-curriculum.md), [CARD-441](../cards/CARD-441-progress-you-can-trust-non-studio-surface.md), [CARD-442](../cards/CARD-442-retire-education-studio-landing.md) (Superseded), [CARD-446](../cards/CARD-446-education-studio-flashcard-quiz-test-players.md) (parent), [CARD-447](../cards/CARD-447-education-studio-operator-strip-and-tutor-context.md), [CARD-448](../cards/CARD-448-education-studio-flashcard-quiz-test-players.md)  
> **Amends**: CARD-435 fork that said Education Studio landing **retires** (dated decision lock below). Extends the earlier "players only" reading of this ADR / CARD-446. No prior ADR had locked Studio retirement.

---

## 1. Context & Problem Statement

CARD-435 locked a Tutor-first Learning OS north star and scaffolded [CARD-442](../cards/CARD-442-retire-education-studio-landing.md) to **retire** the Education Studio landing/bottom-nav panel farm after Tutor+Wiki covered the program. CARD-436..441 shipped Study entry, durable chat quiz/flashcard grading, due reviews, wiki curation, and trustable progress while Studio stayed as reference. The Study education-mode strip (`#chatEducationModeStrip` and Due / Progress / Wiki curate chrome) temporarily hosted operator controls in chat.

Jacob's first product lock (2026-09-23):

> We will NOT remove Education Studio. We will repurpose it to a flash card, quiz, and test player.

Recorded as Option 3 below (Studio stays as **player**; CARD-442 Superseded).

Jacob's follow-on product lock (same day, **continue** after locking the product fork):

1. **Education Studio** = education **operator surface + players**: topic/course selection (saved in Studio), Due reviews, Progress, Wiki curate controls, **and** flashcard/quiz/test players.
2. **Tutor chat** = conversation + skills/tools/wiki templates. The dense UI strip currently in chat (Due reviews / Progress / Wiki curate / education-mode chrome that duplicates Studio) should **move into Education Studio**, not stay as the long-term home.
3. **Context model** (Projects Studio ↔ Developer parallel): whatever topic/course is active/saved in Education Studio, Tutor must be aware of that specifically (inject context like project-path awareness).
4. Learning OS APIs from CARD-438–441 stay; this is UI ownership + context wiring, not ripping durable backends.
5. This ADR already said Studio is player not retired — **extend** it to operator+player; do not contradict.

The retirement end-state in CARD-442 remains dead. The "players only" reading of CARD-446 without operator relocation also dies. AutoReiv needs a clear boundary: Tutor owns coaching + Learning OS skills/tools; Studio owns the education **operator console** and **interactive players**, with Tutor reading Studio's saved active topic/course.

---

## 2. Decision Drivers

* Keep a dedicated interactive surface for flashcards, quizzes, and tests (deck/player UX), not only chat turns.
* Give education a real **operator console** (topic/course selection, Due, Progress, Wiki curate) that is not permanently jammed into Tutor chat chrome.
* Preserve Tutor-first Learning OS skills, durable ledger grades, and Study entry (CARD-436..441 remain valid; APIs stay).
* Mirror Projects Studio → Developer active-project awareness for Education Studio → Tutor topic/course awareness.
* Avoid silent contradiction with CARD-435 / CARD-442 retirement language and with the earlier players-only ADR wording.
* Do not revive CARD-434 monolith-split-as-first-build theatre; operator+player work is focused UI ownership cards.
* Lumina stays separate.

---

## 3. Considered Options

* **Option 1**: Keep CARD-442 — hide/remove `#tab-education` / `#view-education` after Tutor+Wiki cover the program.
* **Option 2**: Leave Studio as the multi-panel Learning OS dashboard forever (Tutor chat grading is optional theatre); chat strip stays the forever operator UI.
* **Option 3**: **Cancel Studio retirement.** Repurpose Education Studio as the flashcard + quiz + test **player** UI only. Tutor/chat Learning OS keeps coaching + durable grading **and** permanently hosts Due/Progress/Wiki curate strip.
* **Option 4 (chosen amendment)**: **Extend Option 3.** Education Studio = **operator surface + players**. Relocate Due/Progress/Wiki curate (and topic/course selection saved in Studio) into Studio. Tutor stays coach with **Studio-injected** active topic/course context. Keep Learning OS APIs from CARD-438–441.

---

## 4. Decision Outcome

Chosen option: **Option 4** (amendment of Option 3). Option 3's "Studio stays; do not retire" lock remains; the role widens from players-only to **operator + players**.

### Decision lock (2026-09-23) — Studio stays (players)

1. **Education Studio stays.** It is **not** retired and is **not** vestigial chrome to delete.
2. **Education Studio role (initial)** = interactive **player** for flashcards, quizzes, and tests (deck/session player UX on `#view-education` / Education tab).
3. **Tutor education mode / Study** remains the coaching + Learning OS skill entry; durable grades stay on Learning OS APIs / agent tools (CARD-438 path).
4. **CARD-442** is **Superseded**. "Retire Education Studio landing" is no longer the end state of the Tutor-first wave.
5. **CARD-446** (then: single player card) was queued after Tutor Learning OS due/wiki/progress cards.
6. **CARD-444 / CARD-445** stay valid Ready work (skill efficiency / turn budget); they do not assume Studio death.
7. **CARD-434** remains Superseded (monolith split is still the wrong first build); player work does not reopen 434.

### Decision update (2026-09-23) — Studio = operator + players

1. **Education Studio role (authoritative)** = education **operator surface + players**:
   - Topic/course selection **saved in Studio** (active education context).
   - Operator controls: **Due reviews**, **Progress**, **Wiki curate**.
   - Interactive **flashcard / quiz / test players**.
2. **Tutor chat role** = conversation + Learning OS skills/tools/wiki templates. Tutor is the **coach**, not the long-term home for dense education operator chrome.
3. **Strip relocation**: Study/Tutor education-mode strip controls that duplicate Studio (Due / Progress / Wiki curate / education-mode operator chrome) **move into Education Studio**. Chat may keep a thin context indicator; the strip is **not** the permanent operator UI.
4. **Context wiring**: Whatever topic/course is active/saved in Education Studio, Tutor **must** be aware of it (inject into Tutor turns analogous to Projects Studio active project path → Developer). Exact persistence/API shape is owned by [CARD-447](../cards/CARD-447-education-studio-operator-strip-and-tutor-context.md): settings key `selected_education_context`, `GET`/`PUT` `/api/education/selected`, localStorage `autoreiv.educationStudio.activeContext.v1`, Tutor via `POST /api/education/tutor/context`.
5. **Backends stay**: CARD-438–441 Learning OS APIs/tools remain; this fork is **UI ownership + context wiring**, not ripping durable backends. Do **not** mark 437–441 Done as wrong — note UI may relocate under this ADR.
6. **Card reshape**: [CARD-446](../cards/CARD-446-education-studio-flashcard-quiz-test-players.md) is the **parent/planning** card for Studio operator+players. Build order: [CARD-447](../cards/CARD-447-education-studio-operator-strip-and-tutor-context.md) (strip + context) **then** [CARD-448](../cards/CARD-448-education-studio-flashcard-quiz-test-players.md) (players). Do not implement frontend moves on the docs lock pass.
7. **CARD-444 / CARD-445** remain Ready unless wording conflicts (Tutor-side efficiency/budget; do not assume chat strip forever).

### Positive Consequences

* Clear product split: Tutor coaches with Studio context; Studio is the education console + players.
* Operators get a focused home for Due/Progress/Wiki curate and deck play without chat chrome sprawl.
* Governance matches Jacob's locks; retirement and players-only-without-operator no longer compete with intent.
* Learning OS ledger APIs remain the durable source of truth.

### Negative Consequences / Trade-offs

* Education tab / `#educationStudio` remains in IA; nav cleanup from CARD-442 does not ship.
* Chat strip shipped on CARD-437/439/440/441 becomes a **temporary** home until CARD-447 relocates controls.
* Player UX (CARD-448) must still call the same durable Learning OS grade paths (no ephemeral Studio-only scores).
* Older CARD-435 / ADR prose that said "Studio retires" or "players only" must be read through this amendment; prefer this lock.

---

## 5. Pros and Cons of Options

### Option 1 (retire Studio)
* Good, because IA shrinks to Study/Tutor + Wiki.
* Bad, because it removes the natural home for interactive deck/test players **and** the education operator console Jacob wants.

### Option 2 (Studio stays as dashboard farm; chat strip forever)
* Good, because no nav change.
* Bad, because it fights Tutor-first Learning OS and keeps panel-farm + chat-strip gravity.

### Option 3 (Studio = player only; strip stays in chat)
* Good, because matches the first lock and keeps durable Tutor rails.
* Bad, because chat remains the forever operator UI and Studio is incomplete as a console.

### Option 4 (Studio = operator + players; Tutor = coach with Studio context)
* Good, because matches the follow-on lock, Projects↔Developer parallel, and keeps durable APIs.
* Bad, because Studio frontend needs focused operator+player cards (446/447/448) instead of a delete or players-only polish.

---

## 6. Follow-up

* Keep [CARD-442](../cards/CARD-442-retire-education-studio-landing.md) Superseded.
* Amend [CARD-435](../cards/CARD-435-education-tutor-first-direction.md) forks and successor table for operator+players.
* Parent program: [CARD-446](../cards/CARD-446-education-studio-flashcard-quiz-test-players.md).
* Implement strip relocation + Tutor context on [CARD-447](../cards/CARD-447-education-studio-operator-strip-and-tutor-context.md) **first**.
* Implement players on [CARD-448](../cards/CARD-448-education-studio-flashcard-quiz-test-players.md) **after** 447.
* Pointer updates: inventory, CARD-437 notes (UI may relocate; Done APIs stand).
