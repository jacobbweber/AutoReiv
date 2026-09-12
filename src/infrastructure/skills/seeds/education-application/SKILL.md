---
name: Education Application
description: Assign Application Exercise Jobs with binary external verify; fail parks/replans; pass advances mastery.
---

# Education Application

Use this runbook when the learner needs **Application**: a real **Exercise Job** where they apply knowledge, graded by **binary external verify** (never LLM self-score).

## Tools / primitives (reuse standing Job / HITL / mastery)

1. Extract Application / Exercise tasks from Wiki (`## Application` / `## Exercise`).
2. Prefer minting a **standing Exercise Job** via catalog resolve (Education Studio mint path).
3. Grade attempts with binary external reference / required-concepts check only.
4. On **fail**: bounded auto-replan or HITL park (CARD-232) and update mastery ledger so retention can resurface.
5. On **pass**: advance mastery ledger. Write outcomes to Wiki and/or agent `memory.db`.

**Forbidden**: LLM self-score theatre; chat toast as Done; inventing a second tutor runtime.

## Order

1. Load or extract the Application exercise item from Wiki.
2. Mint a standing Exercise Job (do not rely on remind-me-later toast).
3. Collect the learner attempt; binary-verify externally.
4. Fail → park/replan + ledger miss; Pass → advance mastery + write-back.

## Done-when

- An Exercise Job was minted (or reused), the attempt was binary-verified, fail parked/replanned or pass advanced mastery, and Wiki/memory write-back landed.
