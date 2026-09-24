---
id: CARD-447
title: "Education Studio Operator Strip + Tutor Topic/Course Context"
status: In Review
created: 2026-09-23
adr: ADR-0059
labels:
  - type:feature
  - area:education
  - area:frontend
  - area:tutor
  - P0
parent: CARD-446
---

# [CARD-447] Education Studio Operator Strip + Tutor Topic/Course Context

> **Status**: In Review
> **Created**: 2026-09-23
> **Baseline**: `qa` after CARD-441 Done + ADR-0059 operator+players amendment
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)
> **Labels**: `type:feature`, `area:education`, `area:frontend`, `area:tutor`, `P0`
> **Parent**: [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)
> **Build order**: **1 of 2** Studio implementation slices (before players [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md))
> **Depends on APIs**: CARD-437..441 Done (Study entry + durable due/curate/progress paths)

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine which strip controls move, thin chat indicator shape, persistence keys — **still no product code** |
| **`build`** | Implement Studio operator surface + Tutor context injection from Studio active topic/course |
| **`merge to qa`** | After In Review + live operator proof on Jarvis Education tab + Tutor awareness |

Do **not** write product code until Jacob says **`build`** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on (hard)** | [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md), [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md), [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md), [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) **Done** (strip + durable APIs exist to relocate / reuse) |
| **Blocked by** | Leaving Due/Progress/Wiki curate permanently in `#chatEducationModeStrip`; Tutor ignoring Studio-saved topic/course; inventing ephemeral-only Studio progress |
| **Related** | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md) durable grades; [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md), [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) Tutor-side Ready |
| **Unlocks** | [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md) players on a real operator console; Tutor coaching grounded like Developer on Projects Studio active path |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Move the dense education **operator** controls out of Tutor chat into **Education Studio**: topic/course selection (saved in Studio), Due reviews, Progress, Wiki curate.
2. Tutor must know the topic/course that is active/saved in Education Studio and inject that context into turns — parallel to Projects Studio active project path awareness for Developer.
3. Tutor chat remains conversation + skills/tools/wiki templates, not the forever operator console.
4. Keep the Learning OS APIs from CARD-438–441; relocate UI ownership, do not rip backends.

### Beat 2: What AutoReiv does now

1. Study entry (`src/web/static/modules/studios/study_entry.js`) binds course via `POST /api/education/course/start` + `POST /api/education/tutor/context` and shows `#chatEducationModeStrip`.
2. Due / Progress / Wiki curate operator panels live on the Tutor education-mode strip (CARD-439 / 441 / 440): e.g. `#chatEducationModeDueBtn`, `#chatEducationModeProgressBtn`, Wiki curate panel chrome.
3. Education Studio still has engineering-heavy Ask / course chrome / quiz panels in `src/web/static/modules/studios/education.js` and `#view-education`, but is not yet the sole operator console for those strip controls.
4. Projects Studio persists an active project and Chat/Developer can surface that path (`chatActiveProjectPill` / projects selected slug+path) — education lacks the same Studio→Tutor contract for topic/course.
5. Durable APIs already exist: mastery due, progress, wiki curate, course start/tutor context.

### Beat 3: What will change

1. Education Studio becomes the home for **topic/course selection saved in Studio** and for **Due / Progress / Wiki curate** operator controls (reuse Learning OS APIs; move or mirror UI from chat strip into `#view-education` / documented Studio chrome).
2. Persist the active education topic/course selection in Studio (local chrome and/or existing course APIs — exact keys locked at **build**; must survive hard-refresh).
3. When Tutor runs in education mode, inject the Studio-active topic/course into Tutor context (extend or call `POST /api/education/tutor/context` / Study entry helpers so Tutor is specifically aware — same product idea as active project path for Developer).
4. Demote chat strip from required operator home: thin context indicator may remain; dense Due/Progress/Wiki curate chrome relocates to Studio (do not require chat strip to operate those flows).
5. Study entry may still open Tutor, but topic/course SoT for "what am I studying" becomes Studio-saved selection once set.

**Out of scope:** Flashcard/quiz/test **player** rebuild ([CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md)); retiring Education Studio; Lumina; CARD-434 monolith split; ripping CARD-438–441 tools/APIs; Tutor skill efficiency ([CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md)); turn-budget defaults ([CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md)); main merge; version bump for docs.

### Beat 4: What dies today

1. Chat education-mode strip as the **permanent** home for Due / Progress / Wiki curate operator UI.
2. Tutor education turns that are unaware of the topic/course the operator saved in Education Studio.
3. Treating CARD-437/439/440/441 Done as "strip stays forever" — those cards shipped durable APIs; UI ownership moves under ADR-0059.

---

## 2. Acceptance criteria

- **[REQ-447-001]** WHEN the operator selects or saves a topic/course in Education Studio, THE SYSTEM SHALL persist that active education context so it survives hard-refresh (documented storage/API path).
- **[REQ-447-002]** WHEN Education Studio has an active saved topic/course, THE Tutor education-mode path SHALL inject that topic/course into Tutor context (documented call path, e.g. tutor context / Study entry helpers) so the coach is specifically aware of it.
- **[REQ-447-003]** WHEN the operator uses Due reviews, Progress, or Wiki curate from Education Studio, THE SYSTEM SHALL drive the same Learning OS API families shipped on CARD-439 / 441 / 440 (no ephemeral-only Studio lists).
- **[REQ-447-004]** WHEN those operator flows work from Studio, THE SYSTEM SHALL NOT require `#chatEducationModeStrip` Due/Progress/Wiki curate chrome as the only operator path (strip may thin or deep-link; Studio is the console).
- **[REQ-447-005]** WHEN Learning OS APIs fail, THE SYSTEM SHALL show failure/empty honestly — no fake due items, fake mastery percentages, or false "library updated".
- **[REQ-447-006]** THE SYSTEM SHALL NOT remove the Education Studio tab/landing as success criteria (Studio stays per ADR-0059).
- **[REQ-447-007]** THE SYSTEM SHALL NOT delete or reverse CARD-438–441 durable agent tools / HTTP contracts on this card.

---

## 3. Proof / live-test notes

1. Open Education Studio; set topic/course; hard-refresh; confirm selection still active.
2. Open Tutor education mode / Study; confirm Tutor context reflects Studio-active topic/course (UI indicator and/or tutor context payload).
3. From Studio: list Due, view Progress, run Wiki curate against durable APIs; hard-refresh; ledger/library still match.
4. Confirm chat strip is not required to complete those three operator flows.
5. Confirm Lumina still opens; Education nav still present.
6. Failure modes: API errors surface; no fake success.
7. Automated: contract tests for Studio-saved context → Tutor injection; Studio operator panels call Learning OS paths; chat strip not sole SoT.

---

## 4. Constraints

- Branch: `feat/card-447-*` from `qa` only after **`build`**.
- **No product code** until **`build`**.
- Reuse CARD-438–441 APIs/tools; do not invent parallel ephemeral stores.
- Do not implement [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md) players on this card.
- Do not implement [CARD-442](./CARD-442-retire-education-studio-landing.md) retirement or [CARD-434](./CARD-434-education-studio-monolith-decomposition.md).
- No main merge, no GitHub PRs, no version bump for docs-only work.
- Plain full sentences; exact paths.

---

## 5. Reply phrases

- Refine strip/context UX: say **`continue`**.
- Start implementation: say **`build`**.
- After live proof: say **`merge to qa`**.


---

## Implementation notes (CARD-447 build)

**Persistence / Tutor injection (locked at build):**

| Path | Role |
|------|------|
| Settings key `selected_education_context` | Durable Studio-active topic/course (Projects `selected_project` parallel) |
| `GET` / `PUT` `/api/education/selected` | HTTP contract for read/write |
| localStorage `autoreiv.educationStudio.activeContext.v1` | Studio chrome mirror (survives hard-refresh) |
| `POST /api/education/tutor/context` | Tutor grounding after Set active / Study entry |
| `#educationOperatorConsole` | Operator home for Due / Progress / Wiki curate (Learning OS APIs) |
| `#chatEducationModeStrip` | Thinned: topic/course indicator + **Studio console** deep-link; Due/Progress/Wiki curate buttons deep-link to Studio |

**Out of scope (unchanged):** CARD-448 players; Studio retirement; version bump.

