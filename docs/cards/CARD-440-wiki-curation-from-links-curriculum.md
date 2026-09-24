---
id: CARD-440
title: "Wiki Curation from Links / Curriculum (Tutor + Learning OS Path)"
status: In Review
created: 2026-09-23
adr: none
labels:
  - type:feature
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-440] Wiki Curation from Links / Curriculum (Tutor + Learning OS Path)

> **Status**: In Review
> **Created**: 2026-09-23
> **Baseline**: `qa` @ `9f2e7b14` (after CARD-435 docs tip)
> **ADR Reference**: none
> **Labels**: `type:feature`, `area:education`, `area:tutor`, `P0`
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Build order**: **5 of 7**.

---

## Gate language (exact reply phrases)

| Jacob reply | Meaning |
|-------------|---------|
| **`continue`** | Refine curation packet, template catalog rules, tag policy — **still no product code** |
| **`build`** | Implement Tutor/Learning OS wiki curation path from links/curriculum |
| **`merge to qa`** | After In Review + live operator proof |

Do **not** write product code until Jacob says **build** on this card.

---

## Depends-on / blocked-by / unlocks

| Relation | Cards |
|----------|-------|
| **Depends on** | [CARD-436](./CARD-436-inventory-tutor-learning-os-rails.md) (template catalog + curation skill id); [CARD-437](./CARD-437-study-entry-tutor-education-mode-thin-shell.md) preferred for operator entry |
| **Blocked by** | Missing inventory of education Wiki templates / curation skill |
| **Unlocks** | Stronger library for quiz/reviews and Studio players ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)); [CARD-442](./CARD-442-retire-education-studio-landing.md) Superseded |

---

## 1. Four Beats

### Beat 1: What Jacob means

1. Wiki is the **library / curated corpus**. Tutor + Learning OS must offer a first-class path to curate from **links and curriculum**, not only Studio side panels.
2. Education templates are **catalogued**; raw sources need **not** all wear education tags.

### Beat 2: What AutoReiv does now

1. Education templates under `data/wiki/02_Resources/_Templates/education-*.md` and application template helpers in `src/application/education/templates.py`.
2. Education Studio Ask/Wiki grounding (`#educationWikiSearchInput`, wiki search in `education.js`) and knowledge-artifact APIs (`POST /api/education/knowledge-artifact`, knowledge-types routes).
3. Priming wiki I/O: `src/application/education/priming_wiki_io.py`, router `src/web/routers/education_priming.py`.
4. General Wiki Studio remains the library surface; education curation is still heavily Studio-adjacent.

### Beat 3: What will change

1. Named Learning OS / Tutor skill path: operator supplies link(s) and/or curriculum outline → curated Wiki note(s) using catalogued education templates where appropriate.
2. Catalog education templates explicitly (from inventory); allow raw/source notes without forcing education tags on every ingest.
3. Durable proof: curated notes exist on disk under the configured wiki root after refresh; operator can open them in Wiki.
4. Do not remove Education Studio wiki chrome yet.

**Out of scope:** Lumina video; full Wiki Studio redesign; Studio players ([CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md)); inventing a second wiki writer that bypasses existing wiki note tools/APIs.

### Beat 4: What dies today

1. Curation-from-curriculum as an Education Studio-only afterthought.
2. Requirement that every raw source note must carry education tags.

---

## 2. Acceptance criteria

- **[REQ-440-001]** WHEN the operator runs wiki curation from Tutor education mode with a link or curriculum outline, THE SYSTEM SHALL create or update durable Wiki note(s) via existing wiki note create/update paths (tools or HTTP already used by Learning OS), not transcript-only text.
- **[REQ-440-002]** WHEN education templates apply, THE SYSTEM SHALL use catalogued templates under `data/wiki/02_Resources/_Templates/education-*.md` (or inventory-locked equivalents); raw sources MAY omit education tags.
- **[REQ-440-003]** WHEN curation fails (fetch/tool/wiki write), THE SYSTEM SHALL surface failure without claiming the library was updated.
- **[REQ-440-004]** THE SYSTEM SHALL NOT remove Education Studio wiki grounding UI on this card.

---

## 3. Proof / live-test notes

1. From Tutor education mode, curate one link and one short curriculum bullet list into Wiki; open notes in Wiki Studio / filesystem under wiki root.
2. Confirm template usage where claimed; confirm at least one raw/source note without education tag if that path is exercised.
3. Failure: bad URL or wiki write denied → error, no fake success.
4. Automated: test curation skill/API writes a note path that `wiki_note_read` (or equivalent) returns.

---

## 4. Constraints

- Branch: `feat/card-440-*` from `qa` after **build**.
- **No product code** until **build**.
- No `main` merge, no GitHub PRs, no version bump for docs-only.
- Reuse wiki note tools/APIs; no dual corpus truth.

---



## Implementation note (In Review)

- Branch: `feat/card-440-wiki-curation-from-links-curriculum`
- Durable API: `POST /api/education/wiki/curate`, `GET /api/education/wiki/templates`
- Tools: `education_wiki_template_catalog`, `education_wiki_curate_from_link`, `education_wiki_curate_from_curriculum`
- Study UI: `#chatEducationModeCurateBtn` / `#chatEducationModeCuratePanel`
- After live proof: say **`merge to qa`**

## 5. Reply phrases

- Refine curation contract: say **continue**.
- Start implementation: say **build**.
- After live proof: say **merge to qa**.
