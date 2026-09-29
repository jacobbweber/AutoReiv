---
id: CARD-581
title: "write_card treats a new card that mentions another card as an edit of that card (refuses it, or overwrites it)"
status: Done
completed: 2026-09-29
created: 2026-09-29
branch: fix/card-581-write-card-mentioned-id
related:
  - CARD-562
  - CARD-563
labels:
  - type:bug
  - area:cards
  - P1
needs_decision: none
milestone: M24
---

# [CARD-581] write_card treats a new card that mentions another card as an edit of that card

> **Status**: Done (merged into qa 2026-09-29)
> **Labels**: `type:bug`, `area:cards`, `P1`

## Why

Found in the 2026-09-29 battery test (throwaway :8770, Architect on Spark, task "write a Ready card for multiply()").
The Architect's new card said "Out of scope: add() (CARD-1), divide() (CARD-2)". `CardTools._existing_card` took the
first `CARD-N` anywhere in the content (`extract_card_id("", content)`), found CARD-1 (In Review) and refused three
times with "This card is In Review ... Architect does not edit it", even when the model passed
`filename="CARD-3-multiply-returns-product.md"`. The same path lets the Developer **overwrite** an existing Proposed card
when its new Proposed card mentions it (statuses match, so no refusal): data loss.

## Change

- `src/application/skills/card_tools.py`: `own_card_id(content)` reads only the card's own id (frontmatter `id:` or the
  first heading, e.g. `# [CARD-563] ...`), never a mentioned id. `write_card` uses it to find an existing card, to pick
  the requested id for a new Architect card, and to decide whether to stamp the id.
- Tests `tests/unit/skills/test_card581_write_card_mentioned_id.py`: the three behaviour tests fail on the old code
  (Architect refused, Developer overwrote CARD-3, filename id ignored); editing by the card's own id still works.

## Acceptance

- [x] A new card that mentions other cards gets the next id and leaves the mentioned cards untouched.
- [x] Editing a card by its own frontmatter id or heading still edits it.

## Log

- 2026-09-29: fixed on the branch with tests.
- 2026-09-29: preflight --fast --base qa GREEN. Jacob: merge to qa (battery brief allows merging small fixes). Done; merged into qa.
