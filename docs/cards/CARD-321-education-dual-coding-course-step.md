# [CARD-321] Education Learning OS — Dual Coding as real course step

> **Status**: In Review
> **Created**: 2026-09-14
> **Branch**: `feat/card-321-education-dual-coding-course-step`
> **Depends**: CARD-320
> **Labels**: type:feature, P0, Education, LearningOS, DualCoding, Course, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Dual Coding is a **real ordered course step** (player / diagrams), not jump-only chrome.
2. Completing the step writes a **Wiki artifact** + **ledger anchors**.
3. Stays inside the `education_course` pipeline from CARD-320 — same ordered course path, not a parallel mode.

### Beat 2: What AutoReiv Does Now
1. CARD-320 has durable course + jump-to-step; Dual Coding was deferred on that card.
2. CARD-238 Dual skills may exist, but there is **no course-step chrome / player** wired into the ordered course pipeline.
3. Dual Coding is not yet a first-class step that advances `current_step` with Wiki + ledger write-back.

### Beat 3: What Will Change
1. Dual Coding step appears in course order with player / diagram path.
2. On complete: Wiki + ledger write-back (reuse Priming/Retrieval patterns).
3. TDD first + Jarvis live smoke proving course step advance + durable artifacts.

---

## 2. Acceptance

- [x] **[REQ-EDU-DUAL-001]**: Dual Coding is an ordered `education_course` step (not jump-only chrome).
- [x] **[REQ-EDU-DUAL-002]**: Player / diagram path is usable for the Dual Coding step.
- [x] **[REQ-EDU-DUAL-003]**: Step complete writes Wiki artifact + ledger anchors in agent `memory.db`.
- [x] **[REQ-EDU-DUAL-004]**: Stays inside CARD-320 course pipeline (advances `current_step` / status honestly).
- [x] **[REQ-EDU-DUAL-005]**: Proof: failing test → green; Jarvis live smoke. No toast-only Done.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Amplifiers / Lumina polish
- Adaptive depth / mastery ladder chrome
- Tutor agent runtime

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

- After scaffold → Jacob: **build** (or **build CARD-321**)
- After live OK → Jacob: **merge to qa**
