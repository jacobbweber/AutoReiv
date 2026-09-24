---
id: CARD-435
title: "Education Tutor-First Direction: Learning OS Rails, Wiki Library, Studio as Player"
status: Ready
created: 2026-09-23
adr: ADR-0059
labels:
  - type:architecture
  - type:planning
  - area:ux
  - area:education
  - domain:education
  - area:tutor
  - P0
---

# [CARD-435] Education Tutor-First Direction: Learning OS Rails, Wiki Library, Studio as Player

> **Status**: Ready
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `752c8f6f` (v0.42.0)
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md) (amends Studio retirement fork)
> **Labels**: `type:architecture`, `type:planning`, `area:ux`, `area:education`, `domain:education`, `area:tutor`, `P0`
> **Supersedes**: [CARD-434](./CARD-434-education-studio-monolith-decomposition.md) (Education Studio monolith decomposition — wrong first build because the page is being retired)

---

## Gate language (exact reply phrases)

This card **requires a decision/design phase before build**.

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Discuss, refine inventory, compare options, lock successor slices — **still no product code** |
| **`build`** | Only after the north-star forks below are locked and successor implementation cards are scaffolded |
| **`merge to qa`** | Only after In Review + live operator test of eventual implementation card(s) |

Do **not** treat scaffolding this Ready card as approval to implement. Do **not** implement CARD-434.

---

## Locked product north star (verbatim substance)

These decisions are **locked** on this planning card. Successor build cards must obey them.

1. **Learning OS is the Tutor’s operating system** — named skills and templates, not open-chat vibes.
2. **Wiki is the library / curated corpus** — the durable knowledge surface learners and Tutor skills draw from.
3. **Lumina Studio stays** — separate video effort later; do not fold Lumina into Education Studio cleanup.
4. **Education Studio as a dashboard landing page / bottom-nav destination RETIRES** — do not polish it, do not monolith-split it, do not treat `src/web/static/modules/studios/education.js` decomposition as the first Education build.
5. **Study entry = Tutor in education mode** (or a thin Study entry that is Tutor + course context), **not** the current panel farm.
6. **Day-one reshape needs** (what successor slices must deliver):
   - Start / resume topic
   - Quiz / flashcard turns in chat with durable grading
   - Due reviews
   - Wiki curation from links / curriculum
   - Hard Learning OS rails
   - Progress you can trust
7. **CARD-434 (education.js monolith decomposition) is the WRONG first build** because the Education Studio page is being retired. That card is **Superseded** by this planning card.

---

## 1. Four Beats

### Beat 1: What this means

1. Education work after Tools / Agent-builder is **not** “make Education Studio maintainable.” It is **reshape how study starts**: Tutor + Learning OS + Wiki.
2. The operator/learner should enter study through **Tutor in education mode** (or a thin Study shell that is Tutor plus course context), not a multi-panel Education Studio farm.
3. Learning OS remains the structured rails (named skills, templates, course/ledger/retrieval/retention contracts already shipped under CARD-237..334 / 315..334). Open chat without rails is not the product.
4. Wiki remains the curated corpus; day-one must make curation from links/curriculum a first-class Tutor/Learning OS path, not a side panel afterthought.
5. Lumina Studio is out of scope for this reshape except “leave it alone / later video effort.”
6. CARD-434’s monolith split of `src/web/static/modules/studios/education.js` is cancelled as a first build: retiring the landing page makes that refactor theatre.

### Beat 2: What AutoReiv does now

1. On tip `752c8f6f`, `src/web/static/modules/studios/education.js` is still a large Education Studio module (~2,569 lines) with Ask, course chrome, quiz/SRS, labs, tutor entry, amplifiers, and session chrome.
2. Learning OS backend/cards CARD-237..334 / 315..334 are Done on `qa`/`main` (course, ledger, retrieval, retention, tutor, amplifiers, delivery profiles) — the rails exist; the **entry UX** is still the Education Studio panel farm.
3. Tutor exists as education discuss/Socratic entry inside Education Studio and as agent/skill surfaces elsewhere; it is not yet the sole Study destination.
4. Wiki is the library surface; Education Studio still owns a lot of learner chrome that should be Tutor turns + durable Learning OS state instead.
5. Lumina Studio remains a separate studio; do not couple this card to Lumina video work.
6. CARD-434 was scaffolded Ready to decompose `education.js` into `src/web/static/modules/studios/education/*` submodules. That direction is wrong given retirement of the page.

### Beat 3: What will change

1. **Product entry**: Study / education mode lands on Tutor (education mode) or a thin Study entry = Tutor + course context. Education Studio is **not** the coaching destination; per ADR-0059 it **stays** and is repurposed as the flashcard/quiz/test **player** ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)) — do not hide/remove the Education tab.
2. **Learning OS as Tutor OS**: Tutor turns invoke named Learning OS skills/templates (start/resume topic, quiz, flashcards, due reviews, wiki curation) with durable state — not freeform chat vibes.
3. **Durable grading and progress**: Quiz/flashcard turns in chat write durable grades and progress the operator can trust (ledger / Learning OS stores — no ephemeral-only theatre).
4. **Due reviews**: Surface and run due SRS/review work from Tutor education mode.
5. **Wiki curation**: From links/curriculum, Tutor/Learning OS paths curate into the Wiki library (exact paths and APIs locked in successor cards).
6. **Hard rails**: Reject or hard-gate “open chat study” that bypasses Learning OS skill/template contracts.
7. **Successor cards**: CARD-436..441 (Tutor Learning OS) plus CARD-446 (Studio players, last) are the wave. CARD-442 retirement is **Superseded**. This planning card still does **not** contain implementation code. Say **build** on each successor individually. Studio **player** card ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)) stays last.

Scaffolded successor implementation cards (**build order**; earlier = build first; Studio **player** card is **last** so earlier cards capture Tutor Learning OS while Studio remains for later player work):

| Order | Card | Intent |
| --- | --- | --- |
| 1 | [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md) | Inventory + Tutor Learning OS rails (named skills/templates; Studio chrome map). Keep Studio alive. **In Review** on feat branch. |
| 2 | [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md) | Study entry = Tutor education mode (thin shell). Do **not** remove Education Studio nav/landing yet. |
| 3 | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) | Chat quiz/flashcard turns + durable Learning OS grading (not ephemeral theatre). |
| 4 | [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md) | Due SRS/reviews surfaced and completed from Tutor education mode / Study. |
| 5 | [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md) | Wiki curation from links/curriculum via Tutor/Learning OS; education templates catalogued; raw sources need not all wear education tags. |
| 6 | [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) | Progress you can trust on non-Studio surfaces (Tutor cards and/or Wiki views). |
| 7 (LAST) | [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) | **Build Education Studio as flashcard + quiz + test players** (interactive decks). Depends on 438 Done and 439/440/441 Done or In Review with proof. **Not** retirement ([CARD-442](./CARD-442-retire-education-studio-landing.md) Superseded). **Not** a monolith split of ducation.js. |

**Studio player card is last.** Do not start CARD-446 before CARD-438 is Done and CARD-439..441 prove Tutor Learning OS coverage. Do **not** implement CARD-442 retirement.


### Beat 4: What dies

1. **Education Studio as a destination** — dashboard landing page and bottom-nav entry for “Education” as a panel farm. Do not polish it.
2. **CARD-434 monolith decomposition** as the next Education build — superseded; do not cut `feat/card-434-*` or port CARD-400’s `education/` submodule split as the first slice.
3. **Open-chat study vibes** as the product story — Learning OS named skills/templates are the rails.
4. **Ephemeral quiz/progress theatre** — grades and progress must be durable and operator-trustable.
5. No change required to Lumina Studio on this card (it stays; video work is later).

---

## 2. Product-policy forks (locked on north star)

| # | Fork | Locked decision |
|---|------|-----------------|
| 1 | Study entry | **Tutor in education mode** (or thin Study = Tutor + course context). Not the Education Studio panel farm. |
| 2 | Education Studio landing / bottom-nav | **Stays** (ADR-0059). Repurposed as flashcard/quiz/test **player** ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)). Not the Study/coaching destination. Do not monolith-split as first build (CARD-434 still Superseded). |
| 3 | Learning OS role | **Tutor’s operating system** — named skills/templates. |
| 4 | Wiki role | **Library / curated corpus**. |
| 5 | Lumina Studio | **Stays**; separate video effort later. |
| 6 | CARD-434 | **Superseded** by this card; wrong first build. |
| 7 | Day-one reshape | Start/resume topic; quiz/flashcard chat turns + durable grading; due reviews; wiki curation from links/curriculum; hard Learning OS rails; progress you can trust. |

Planning may continue (`continue`); **no product code** until Jacob says **build** and successor cards are scaffolded.

---

## 3. Acceptance criteria (planning card)

- **[REQ-435-001]** This card locks the Tutor-first north star (Beats + forks) without inventing a dual Education Studio + Tutor product story.
- **[REQ-435-002]** CARD-434 is marked **Superseded** with a pointer to this card; file retained; no monolith decomposition work starts from 434.
- **[REQ-435-003]** Successor implementation slices are named here; actual build cards are scaffolded only after Jacob says to build on successors — **no implementation code in this card**.
- **[REQ-435-004]** Anti-theatre lock for successors: every slice must specify durable state, Studio/operator path, failure modes, and proof (exact paths and APIs in those later cards).
- **[REQ-435-005]** Lumina Studio is explicitly out of scope for retirement/reshape on this program except “leave alone / later.”

---

## 4. Constraints

- Docs / planning only on this card until Jacob says **build**.
- Branch any future implementation off `qa` only; do not merge to `main` from this program’s cards unless Jacob explicitly says so later.
- Do **not** create GitHub PRs from this scaffolding work; local `qa` docs commit + push only for this card pair.
- Do **not** bump version for docs-only card scaffolding.
- Do **not** implement CARD-434 or revive `feat/card-400-education-monolith-decomposition` as the Education first build.
- Exact reply phrases: **continue** / **build** / **merge to qa**.
- Plain full sentences and exact paths in successor cards when scaffolded.

---

## 5. Reply Phrases

- Scaffold / planning review: say **continue** if the Four Beats or forks need edits.
- After successors are scaffolded and forks stay locked: say **build** (on those successor cards — not a mega-build from this parent alone).
- After live test of an implementation card: say **merge to qa**.

---

## 6. Relationship to CARD-434

| Card | Role |
|------|------|
| [CARD-434](./CARD-434-education-studio-monolith-decomposition.md) | **Superseded**. Was Ready to split `src/web/static/modules/studios/education.js` into `src/web/static/modules/studios/education/*`. Wrong first build because Education Studio landing is retiring. |
| **CARD-435 (this card)** | Planning parent for Tutor-first Study entry, Learning OS rails, Wiki library, Education Studio **player** repurpose (ADR-0059). |

Do not delete CARD-434. Do not implement it.

---



---

## Amendment (2026-09-23) — Education Studio stays (player lock)

Jacob product lock: **We will NOT remove Education Studio. We will repurpose it to a flash card, quiz, and test player.**

Recorded in [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md).

| Was (pre-lock) | Now |
|----------------|-----|
| Fork: Education Studio landing / bottom-nav **retires** | Studio **stays**; role = flashcard / quiz / test **player** |
| Successor LAST: [CARD-442](./CARD-442-retire-education-studio-landing.md) retire landing | CARD-442 **Superseded**; LAST = [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) players |
| Beat 4 / dies: Studio as destination | Softened: Studio is no longer the Study/coaching destination (Tutor is), but it remains as the dedicated **player** surface — not deleted |

Tutor-first Learning OS skills, Study entry, durable grading, due reviews, wiki curation, and progress cards (**436..441**, plus **444/445**) remain valid. Do **not** implement CARD-442 retirement.

## Successor cards (build order)

Studio **player** card is **last** ([ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)). Earlier cards capture Tutor Learning OS while Studio remains (later as player). [CARD-442](./CARD-442-retire-education-studio-landing.md) is **Superseded**.

1. [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md) - Inventory + Tutor Learning OS rails (**Done**)
2. [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md) - Study entry = Tutor education mode (**Done**)
3. [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) - Chat quiz/flashcard + durable grading (**Done**)
4. [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md) - Due reviews in Tutor education mode
5. [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md) - Wiki curation from links/curriculum
6. [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) - Progress you can trust (Tutor/Wiki surfaces; Studio player is separate)
7. [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) - **LAST:** Education Studio flashcard / quiz / test **players** (depends on 438 Done + 439..441 Done or In Review with proof)

Related Ready (not in the 1..7 spine): [CARD-443](./CARD-443-platform-tutor-pack-appdata-sync.md), [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md), [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md).

This planning parent stays **Ready** while guiding the wave. Say **build** on each successor card individually - not a mega-build from this parent alone. No product code until Jacob says **build** on that card.

