---
id: CARD-446
title: "Education Studio Operator + Players (Parent Program; ADR-0059 Amendment)"
status: Ready
created: 2026-09-23
adr: ADR-0059
labels:
  - type:architecture
  - type:planning
  - area:education
  - area:frontend
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-446] Education Studio Operator + Players (Parent Program; ADR-0059 Amendment)

> **Status**: Ready
> **Created**: 2026-09-23
> **Baseline**: `qa` after CARD-441 Done + ADR-0059 operator+players amendment
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md) (amended: Studio = operator + players)
> **Labels**: `type:architecture`, `type:planning`, `area:education`, `area:frontend`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **Parent** for Studio wave. Implementation slices: [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md) **then** [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md). Do **not** mega-build from this parent alone.
> **Supersedes retirement intent of**: [CARD-442](./CARD-442-retire-education-studio-landing.md)
> **Extends**: earlier "players only" reading of this card / ADR-0059

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine operator vs player split, successor slice boundaries, context injection shape — **still no product code** |
| **`build`** | Say **`build`** on the next implementation slice ([CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md) first), not a mega-build from this parent |
| **`merge to qa`** | After In Review + live operator proof on the active implementation card |

Do **not** write product code from this parent until Jacob says **`build`** on a successor slice.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on (hard)** | [CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md), [CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md), [CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md), [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md) **Done** (durable Learning OS APIs + temporary chat strip exist) |
| **Blocked by** | Treating chat strip as permanent operator UI; players-only Studio without operator relocation; retiring Studio ([CARD-442](./CARD-442-retire-education-studio-landing.md)); ripping CARD-438–441 backends |
| **Related** | [CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md), [CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md) stay Tutor-side Ready; they do not block Studio operator/player work |
| **Unlocks** | Education Studio as durable education **operator console + players**; Tutor coach with Studio topic/course context ([ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)) |

**Explicit:** Tutor Learning OS APIs from CARD-438–441 **stay**. This program is **UI ownership + context wiring**, then players. Studio is **kept** and **extended**, not retired.

---

## Successor build order (clear)

| Order | Card | Intent | Status |
| --- | --- | --- | --- |
| Parent | **CARD-446 (this card)** | Lock Studio = operator + players; point successors; no product code | Ready |
| 1 (next build) | [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md) | Relocate Due / Progress / Wiki curate (+ topic/course selection saved in Studio) out of chat strip into Education Studio; wire Tutor awareness of Studio active topic/course (Projects Studio ↔ Developer parallel) | Ready |
| 2 | [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md) | Flashcard / quiz / test **players** on Education Studio; durable Learning OS grades | Ready |

Say **`build`** on **CARD-447** to start product code for this wave.

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Chat education-mode strip was a **temporary** home for Due / Progress / Wiki curate / education-mode operator chrome.
2. **Education Studio** is the real education **console + players**: topic/course selection saved in Studio, Due, Progress, Wiki curate, **and** flashcard/quiz/test players.
3. **Tutor** stays the coach (conversation + skills/tools/wiki templates) and must be aware of the topic/course active in Studio — same idea as Projects Studio active project path for Developer.
4. Do **not** remove Education Studio. Do **not** leave "players only" as the reading of this program.

### Beat 2: What AutoReiv does now

1. `#tab-education` / `#view-education` / `#educationStudio` still present; `education.js` owns Ask, course chrome, quiz/SRS panels, labs, amplifiers (engineering-heavy panel farm, not yet a focused operator+player console).
2. Study entry (CARD-437) opens Tutor education mode; `#chatEducationModeStrip` hosts topic/course/skill chrome.
3. CARD-439 / 440 / 441 added **Due reviews**, **Wiki curate**, and **Progress** panels onto the Tutor education-mode strip (temporary operator home).
4. Durable Learning OS grade/due/curation/progress APIs and Tutor tools from CARD-438–441 are live.
5. ADR-0059 initially locked Studio as **players** only; CARD-442 retirement remains Superseded.
6. Lumina remains a separate studio and is out of scope.

### Beat 3: What will change

1. **Governance lock**: Studio role = **operator surface + players** ([ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md) amendment).
2. **CARD-447**: Move strip operator UI into Studio; persist/select active topic/course in Studio; inject that context into Tutor (like active project path).
3. **CARD-448**: Refocus Studio interactive UX into flashcard / quiz / test players on the same durable Learning OS paths.
4. Tutor chat stays coaching; thin context indicator may remain; dense strip is not the long-term operator UI.
5. Prune or demote non-player / non-operator panel-farm chrome only as needed for honest console+players — **not** CARD-434 monolith-split-as-success and **not** nav retirement.

**Out of scope (this parent):** Implementing frontend moves; retiring/hiding `#tab-education`; Lumina; CARD-434 submodule decomposition as the goal; Tutor skill efficiency ([CARD-444](./CARD-444-flashcard-turn-skill-efficiency.md)); turn-budget defaults ([CARD-445](./CARD-445-tutor-education-mode-default-turn-budget.md)); merging to main; version bump solely for docs; ripping CARD-438–441 APIs.

### Beat 4: What dies today

1. **"Retire Education Studio landing"** as the end state of CARD-442 / the CARD-435 retirement fork.
2. **Chat strip as permanent education operator UI.**
3. **"Players only"** reading of CARD-446 / ADR-0059 without operator relocation and Tutor↔Studio context.
4. Treating Education Studio as disposable vestigial chrome once Tutor covers chat turns.
5. Player or operator UX that shows grades/progress without Learning OS ledger writes.

---

## 2. Acceptance criteria (planning parent)

- **[REQ-446-001]** This card locks Education Studio as **operator surface + players** and Tutor as coach with Studio topic/course context, matching [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md).
- **[REQ-446-002]** Successor implementation cards [CARD-447](./CARD-447-education-studio-operator-strip-and-tutor-context.md) and [CARD-448](./CARD-448-education-studio-flashcard-quiz-test-players.md) are scaffolded Ready with plain full requirements and a clear build order (447 then 448).
- **[REQ-446-003]** THE PROGRAM SHALL NOT treat removing Education Studio or keeping chat strip forever as success.
- **[REQ-446-004]** THE PROGRAM SHALL NOT rip or reverse CARD-438–441 durable Learning OS APIs; UI may relocate under ADR-0059.
- **[REQ-446-005]** Lumina Studio SHALL remain available (not retired or coupled by this program).
- **[REQ-446-006]** THE SYSTEM SHALL NOT treat splitting `education.js` into `education/*` submodules as success criteria (CARD-434 stays Superseded).

---

## 3. Proof / live-test notes

Proof lives on successor cards:

1. CARD-447: Studio hosts Due / Progress / Wiki curate + saved topic/course; Tutor turns see that context; chat strip is no longer the required operator home; hard-refresh keeps Studio selection.
2. CARD-448: flashcard / quiz / test players write durable Learning OS grades; hard-refresh shows ledger progress; Study/Tutor coaching still works; Lumina still opens.

---

## 4. Constraints

- Docs / planning only on this parent until Jacob says **`build`** on CARD-447 (then CARD-448).
- Branch any implementation off `qa` only after **`build`** on that slice.
- Do not implement [CARD-442](./CARD-442-retire-education-studio-landing.md) retirement.
- Do not implement [CARD-434](./CARD-434-education-studio-monolith-decomposition.md).
- No main merge, no GitHub PRs, no version bump for docs-only scaffolding.
- Plain full sentences; exact paths.

---

## 5. Reply phrases

- Refine program / successors: say **`continue`**.
- Start implementation: say **`build`** on **CARD-447** (then later **`build`** on **CARD-448**).
- After live proof on a slice: say **`merge to qa`**.
