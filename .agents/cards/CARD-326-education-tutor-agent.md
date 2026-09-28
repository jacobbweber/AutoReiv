# [CARD-326] Education Learning OS — Tutor agent (Wiki + ledger aware)

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/card-326-education-tutor-agent`
> **Depends**: CARD-316–320 (+ 321–325 paths preferred)
> **Labels**: type:feature, P0, Education, LearningOS, Tutor, AgentPack, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Tutor agent specializes in discussion for the **active Education topic**.
2. Context includes curated Wiki docs + grades/scores from the ledger — not a second tutor DB.
3. HITL-safe; prove context on live Ask.

### Beat 2: What AutoReiv Does Now
1. No dedicated tutor pack/agent wired to Education topic + `memory.db` ledger.
2. Education Studio lacks a first-class Tutor entry that loads Wiki + `education_mastery` / learner for the active topic.
3. Risk of inventing parallel tutor storage — explicitly forbidden.

### Beat 3: What Will Change
1. Tutor pack/agent + Education Studio entry.
2. Loads Wiki (templated artifacts) + education_mastery / learner for active topic from the **same** agent `memory.db`.
3. HITL-safe; prove context on live Ask (Jarvis smoke).

---

## 2. Acceptance

- [x] **[REQ-EDU-TUTOR-001]**: Tutor pack/agent exists and is reachable from Education Studio for the active topic.
- [x] **[REQ-EDU-TUTOR-002]**: Context loads curated Wiki docs + ledger grades/scores (`education_mastery` / learner) — same `memory.db` only.
- [x] **[REQ-EDU-TUTOR-003]**: Never invents a second tutor `storage.db` / parallel brain.
- [x] **[REQ-EDU-TUTOR-004]**: HITL-safe; live Ask proves topic Wiki + ledger context. TDD + Jarvis smoke.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Adaptive depth / growth portfolio / Studio chrome pass (CARD-327)
- Amplifiers / Lumina (CARD-328)
- Replacing CARD-320 course pipeline with tutor-only flow

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

- After scaffold → Jacob: **build** (or **build CARD-326**)
- After live OK → Jacob: **merge to qa**
