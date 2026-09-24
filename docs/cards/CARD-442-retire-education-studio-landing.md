---
id: CARD-442
title: "Retire Education Studio Landing (Last; After Tutor+Wiki Cover the Program)"
status: Superseded
created: 2026-09-23
adr: ADR-0059
labels:
  - type:architecture
  - area:education
  - area:tutor
  - P0
parent: CARD-435
---

# [CARD-442] Retire Education Studio Landing (Last; After Tutor+Wiki Cover the Program)

> **Status**: Superseded
> **Created**: 2026-09-23
> **Baseline**: qa @ 9f2e7b14 (after CARD-435 docs tip)
> **ADR Reference**: [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)
> **Labels**: 	ype:architecture, rea:education, rea:tutor, P0
> **Parent**: [CARD-435](./CARD-435-education-tutor-first-direction.md)
> **Superseded by**: [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) + [ADR-0059](../adr/0059-education-studio-as-quiz-flashcard-and-test-player.md)
> **Supersession note** (2026-09-23): Do **not** implement this card. Jacob locked: Education Studio is **not** removed; it is **repurposed** as the flashcard / quiz / test **player**. Retirement of the Education landing is cancelled. File retained for history. Build the player on CARD-446 (last).

---

## Historical intent (do not build)

This card previously ordered: remove/hide #tab-education / #view-education after CARD-436..441 proved Tutor+Wiki cover the program, and redirect legacy Education entry to Tutor education mode / Study. That end state is **dead**. See ADR-0059 decision lock and CARD-446.

Original build-order note: was **7 of 7 — LAST** under the retirement plan. Successor **last** card is now CARD-446 (players), not retirement.

## Pointers

| Was | Now |
|-----|-----|
| Retire Education Studio landing | **Keep** Studio; build players on [CARD-446](./CARD-446-education-studio-flashcard-quiz-test-players.md) |
| Tutor-first Study / Learning OS | Still valid ([CARD-435](./CARD-435-education-tutor-first-direction.md) amended) |
| CARD-434 monolith split | Still **Superseded** (wrong first build) |

Do not delete this file. Do not cut eat/card-442-*.
