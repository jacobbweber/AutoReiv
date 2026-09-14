# [CARD-324] Education Learning OS — Construction / Application labs with graded pressure

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: CARD-320+ course path; CARD-322 templates preferred
> **Labels**: type:feature, P0, Education, LearningOS, Construction, Application, Labs, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Construction / Application labs are real course steps with **graded pressure** — not optional sandbox theatre.
2. Lab outcomes write durable Wiki + ledger evidence (templated).
3. Miss / incomplete paths feed honest mastery / Retention behaviour — no fake pass.

### Beat 2: What AutoReiv Does Now
1. Course steps cover core Learning OS sequence gaps remaining after Dual / Elaboration cards.
2. Labs / application pressure are not yet a durable graded course step with ledger write-back.
3. Risk of “lab Done” toast without score / artifact anchors.

### Beat 3: What Will Change
1. Construction / Application lab step(s) in course order with graded pressure.
2. Wiki + ledger write-back for lab outcomes / scores (templates).
3. TDD + Jarvis live smoke; binary or explicit grade gate — no LLM self-score theatre.

---

## 2. Acceptance

- [ ] **[REQ-EDU-LAB-001]**: Construction / Application labs exist as ordered course step(s) with graded pressure.
- [ ] **[REQ-EDU-LAB-002]**: Lab complete / grade writes templated Wiki artifact + ledger anchors.
- [ ] **[REQ-EDU-LAB-003]**: Miss / incomplete does not fake mastery; ties to existing Retention / mastery honesty where applicable.
- [ ] **[REQ-EDU-LAB-004]**: Proof: failing test → green; Jarvis live smoke. No toast-only Done.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Environment / Analysis→Retention handoff harden (CARD-325)
- Tutor agent
- Amplifiers / Lumina

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

- After scaffold → Jacob: **build** (or **build CARD-324**)
- After live OK → Jacob: **merge to qa**
