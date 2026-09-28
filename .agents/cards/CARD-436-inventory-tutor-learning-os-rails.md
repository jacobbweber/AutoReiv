---
id: CARD-436
title: "Inventory + Tutor Learning OS Rails (Named Skills/Templates; Studio Chrome Map)"
status: Done
created: 2026-09-23
adr: none
labels:
  - type:architecture
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-436] Inventory + Tutor Learning OS Rails (Named Skills/Templates; Studio Chrome Map)

> **Status**: Done
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none (draft only if lasting Tutor/Learning OS skill contracts change)
> **Labels**: `type:architecture`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **1 of 7** (first Education Tutor-first successor). Education Studio **player** is last ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)); [CARD-442](./CARD-442-retire-education-studio-landing.md) Superseded.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine inventory targets, skill/template names, or Studio→Tutor map — **still no product code** |
| **`build`** | Implement this card only (inventory artifact + Tutor Learning OS rail bindings). Do **not** retire Education Studio. |
| **`merge to qa`** | Completed after live operator proof; merge to `qa` requested 2026-09-23 (EDT) |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-435](./CARD-435-education-tutor-first-direction.md) Ready (north star locked) |
| **Blocked by** | Nothing else in this wave |
| **Unlocks** | [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md) through [CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md); feeds the retirement proof checklist on [CARD-442](./CARD-442-retire-education-studio-landing.md) |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Before any Education Studio UI dies, capture everything the education program and Tutor skills need: skills, templates, APIs, durable stores, and Studio chrome that today carries pedagogy.
2. Bind **Tutor** as the first-class education agent with **named Learning OS skills/templates**, not open-chat vibes.
3. Produce a durable Studio-chrome → Tutor skill inventory so later slices (Study entry, quiz, reviews, wiki curation, progress) know what to re-home and what already exists under Learning OS.

### Beat 2: What AutoReiv does now

1. Education Studio lives in `src/web/static/modules/studios/education.js` (~2,737 lines) and `src/web/templates/index.html` (`#tab-education`, `#view-education`, `#educationStudio`) with Ask, course chrome, quiz/SRS, labs, tutor discuss, amplifiers, environment, and session chrome.
2. Learning OS application code already ships under `src/application/education/` (`course.py`, `quiz_engine.py`, `srs.py`, `retention_routine.py`, `tutor.py`, `templates.py`, `learner_model.py`, priming/*, labs, elaboration, construction, application, analysis, environment, visual_amplifiers, knowledge_types).
3. HTTP surface is `src/web/routers/education.py` (`/api/education/course*`, `/api/education/quiz/*`, `/api/education/mastery*`, `/api/education/retention/run`, `/api/education/tutor/context`, elaboration/construction/application/amplifiers/environment/knowledge routes). Priming: `src/web/routers/education_priming.py`.
4. Tutor pack is thin: `platform-packs/tutor/pack.json` and `platform-packs/tutor/skills/socratic-tutoring/SKILL.md` (also mirrored under `platform-packs/autoreiv/skills/socratic-tutoring/`). Education Studio discuss-with-tutor is still Studio-chrome entry, not a sole Study destination.
5. Wiki education templates live under `data/wiki/02_Resources/_Templates/education-*.md` (concept, quiz, flashcard, lab, priming, dual-coding, elaboration, method, portfolio, problem, score, tool, and related).
6. Durable learner state is ledger/SRS/course oriented (mastery due, quiz grade, course steps) — not yet framed as a Tutor skill inventory that successors can cite without spelunking Studio panels.

### Beat 3: What will change

1. **Inventory artifact** (docs and/or checked-in catalog under an exact path chosen at **build**, e.g. `docs/education/tutor-learning-os-inventory.md` or equivalent): map every Education Studio panel/mode in `education.js` / `#view-education` to (a) Learning OS API(s), (b) durable store, (c) Wiki template if any, (d) proposed Tutor skill or template name, (e) keep / re-home / drop-at-retirement.
2. **Tutor Learning OS rails**: define and wire (or document-then-wire if thin) named skills/templates for at least: start/resume topic, quiz turn, flashcard turn, due review, wiki curation, progress summary — bound to existing `/api/education/*` and `src/application/education/*` contracts where they already exist.
3. **Hard rails policy**: document that education-mode Tutor turns must invoke named Learning OS skills/templates; open vibes without rails are out of product story (enforcement may be partial on this card if successors own chat UX — state residual gates explicitly).
4. **Keep Education Studio alive** on this card: no nav removal, no `#view-education` hide, no retirement of `education.js`.

**Out of scope:** Study shell UX ([CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md)); in-chat quiz durability beyond inventory ([CARD-438](./CARD-438-chat-quiz-flashcard-turns-durable-grading.md)); due-review UX ([CARD-439](./CARD-439-due-reviews-in-tutor-education-mode.md)); wiki curation UX ([CARD-440](./CARD-440-wiki-curation-from-links-curriculum.md)); non-Studio progress surface ([CARD-441](./CARD-441-progress-you-can-trust-non-studio-surface.md)); retiring Education Studio ([CARD-442](./CARD-442-retire-education-studio-landing.md)); Lumina product work; version bump; GitHub PRs.

### Beat 4: What dies today

1. Ambiguity about which Studio chrome must be captured before UI retirement.
2. The idea that Tutor education is “just chat” without named Learning OS skills/templates.
3. Nothing on the Education Studio landing itself — the panel farm stays until [CARD-442](./CARD-442-retire-education-studio-landing.md).

---

## 2. Acceptance criteria

- **[REQ-436-001]** WHEN this card is Done, THE SYSTEM (or checked-in docs on `qa`) SHALL include an inventory that maps Education Studio chrome (Ask, course, quiz, flashcards/SRS, labs, tutor discuss, amplifiers, environment, analysis, sessions) to exact paths under `src/application/education/`, `src/web/routers/education.py`, Wiki `education-*` templates, and proposed Tutor skill/template ids.
- **[REQ-436-002]** WHEN Tutor runs in education mode after this card, THE OPERATOR PATH SHALL be able to invoke named Learning OS skills/templates for start/resume topic (at least bound or stubbed with exact ids documented); open vibes without a named skill MUST be documented as non-product or hard-gated.
- **[REQ-436-003]** THE SYSTEM SHALL NOT remove `#tab-education`, `#view-education`, or bottom-nav Education entry on this card.
- **[REQ-436-004]** Anti-theatre: inventory entries for quiz, mastery, retention, and course MUST cite durable APIs (`/api/education/quiz/grade`, `/api/education/mastery*`, `/api/education/course*`, `/api/education/retention/run` or successors) — not UI-only labels.

---

## 3. Proof / live-test notes

1. On Jarvis, open Education Studio and walk Ask → course chrome → quiz → tutor discuss once; confirm inventory rows match live panels.
2. Confirm Tutor pack / skill list shows the named Learning OS education skills (or the documented temporary stub list with follow-on card owners).
3. Failure modes: missing API for a Studio panel → inventory marks gap + owning successor card; do not fake a skill id with no backend.
4. Automated: add or extend a contract test that asserts catalogued skill/template ids resolve (exact test path chosen at **build**).

---

## 4. Constraints

- Branch off `qa` only when Jacob says **build**: `feat/card-436-*`.
- Docs-only scaffolding now; **no product code** until **build**.
- Do not merge to `main`. Do not create GitHub PRs. Do not bump version for docs-only work.
- Do not implement [CARD-434](./CARD-434-education-studio-monolith-decomposition.md). Do not monolith-split `education.js` as the goal.
- Plain full sentences; exact paths; no tip/green-red shorthand aimed at Jacob.

---

## 5. Reply phrases

- Refine inventory: say **continue**.
- Start implementation: say **build**.
- Live proof complete; **merge to qa** requested 2026-09-23 (EDT).


---

## Implementation notes (Done)

**Branch**: `feat/card-436-inventory-tutor-learning-os-rails`

### Delivered

1. **Inventory**: `docs/education/tutor-learning-os-inventory.md` — Studio chrome → Learning OS modules / `/api/education/*` / durable stores / Wiki `education-*` templates / Tutor skill ids / keep|re-home|drop-at-retirement, with honest gaps owned by CARD-437..442.
2. **Tutor Learning OS rails**: named skills under `platform-packs/tutor/skills/`:
   - `start-resume-topic`
   - `quiz-turn`
   - `flashcard-turn`
   - `due-review`
   - `education-wiki-curation`
   - `progress-summary`
   - plus existing `socratic-tutoring` (dialogue method; not a rails bypass)
   Wired in `platform-packs/tutor/pack.json` (`skills` + `allowed_skill`). Hard rails documented in inventory + each SKILL.md + Tutor system prompt.
3. **Contract test**: `tests/unit/agent_packs/test_card_436_tutor_learning_os_skills.py` (pack ids, SKILL.md resolve, inventory catalogue, Studio chrome not removed).
4. **Must-not held**: `#tab-education`, `#view-education`, Education bottom-nav, and `education.js` monolith remain.

### Live proof for Jacob

1. Open Education Studio — confirm Ask → course chrome → quiz → Discuss with Tutor still work.
2. Open Tutor in Agent Studio / skill list — confirm Learning OS skill ids appear (if live pack is `user_modified`, tick new skills once).
3. `pytest tests/unit/agent_packs/test_card_436_tutor_learning_os_skills.py` green.

### Deferred to successors

- Study/Tutor education-mode thin shell + vibes hard-gate UX → CARD-437
- Chat quiz/flashcard durable UX → CARD-438
- Due reviews in Tutor education mode → CARD-439
- Wiki curation from links/curriculum UX → CARD-440
- Non-Studio progress surface → CARD-441
- Retire Education Studio landing → CARD-442
- No `education_*` agent tools invented on this card (skills cite HTTP contracts)

Live proof complete; **merge to qa** requested 2026-09-23 (EDT).


---

## Merge record

- **Status**: Done
- **Merge note**: Jacob said **merge to qa** after the live Tutor proof.
- **Date**: 2026-09-23 (EDT)
- **Target**: qa (no merge to main)
