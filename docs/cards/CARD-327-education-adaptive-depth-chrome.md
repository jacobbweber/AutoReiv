# [CARD-327] Education Learning OS — Adaptive depth + mastery chrome + Studio usability

> **Status**: In Review
> **Created**: 2026-09-14
> **Branch**: `feat/card-327-education-adaptive-depth-chrome`
> **Depends**: CARD-320+
> **Labels**: type:feature, P1, Education, LearningOS, AdaptiveDepth, Mastery, UX, Studio, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Difficulty grows with mastery (kindergarten → masters).
2. Wiki **growth portfolio** per topic/domain + **mastery level indicator** in Education Studio UI.
3. Education chrome must be usable by a real learner (esp. younger): clear course progress, steps, mastery — not ops-dense theatre.

### Beat 2: What AutoReiv Does Now
1. Binary mastery + Retention schedule exist; no adaptive difficulty ladder or Studio mastery chrome.
2. Course chrome from CARD-320 exists but Studio is still hard to follow; Jacob brain dump flagged chrome as desperate.
3. No durable depth/level model bound to real ledger (risk of toast theatre).

### Beat 3: What Will Change
1. Durable depth/level model in `memory.db`; Wiki portfolio notes; Studio mastery indicator bound to real ledger.
2. Usability pass on Education Studio IA/flow (progress, step labels, empty/error states) without inventing new Learning OS engines.
3. Coordinate with UI/UX Design for visual tokens if needed, but **ship operator-visible flow fixes**.

---

## 2. Acceptance

- [x] **[REQ-EDU-DEPTH-001]**: Durable depth/level model in agent `memory.db` (kindergarten→masters ladder or equivalent).
- [x] **[REQ-EDU-DEPTH-002]**: Wiki growth portfolio notes per topic/domain.
- [x] **[REQ-EDU-DEPTH-003]**: Studio mastery indicator bound to real ledger (not toast theatre).
- [x] **[REQ-EDU-DEPTH-004]**: Usability pass: course progress, step labels, empty/error states readable by a real learner.
- [x] **[REQ-EDU-DEPTH-005]**: Proof: TDD + Jarvis live smoke. Labels include UX.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Lumina amplifiers (CARD-328)
- Inventing new Learning OS engines beyond depth + chrome
- Tutor storage.db

## 5. Wave order

1. **CARD-320** — Course + Mastery model (**In Review**)
2. **CARD-321** — Dual Coding as real course step
3. **CARD-322** — Wiki templates for every Education artifact
4. **CARD-323** — Elaboration course step
5. **CARD-324** — Construction / Application labs
6. **CARD-325** — Environment framing + Analysis→Retention handoff
7. **CARD-326** — Tutor agent (Wiki + ledger aware)
8. **CARD-327** — Adaptive depth + mastery chrome + Studio usability
9. **CARD-328** — Amplifiers / Lumina polish (**P2**, last)

Hold merge to `qa` until Jacob says **merge to qa**. Do not merge earlier cards into `qa` from this wave without Jacob.


## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-327**)
- After live OK → Jacob: **merge to qa**
