# [CARD-323] Education Learning OS — Elaboration course step

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: CARD-320 / CARD-321 / CARD-322 paths
> **Labels**: type:feature, P0, Education, LearningOS, Elaboration, Course, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Elaboration is a real ordered course step: learner **explains in their own words**.
2. Outcome is durable — Wiki artifact + ledger anchors — not chat vapour.
3. Fits the CARD-320 course pipeline like Dual Coding / Priming / Retrieval.

### Beat 2: What AutoReiv Does Now
1. Course pipeline (CARD-320) + Dual Coding step (CARD-321) land ordered steps; Elaboration is not yet a first-class course step.
2. Explain-in-own-words may exist as Ask chrome / skills, but without durable course-step write-back + step advance.
3. No enforced Elaboration Wiki template path guaranteed after CARD-322.

### Beat 3: What Will Change
1. Elaboration step in course order with explain-in-own-words UX.
2. Durable write-back (Wiki + ledger) using Education templates.
3. TDD + Jarvis live smoke proving step complete advances course honestly.

---

## 2. Acceptance

- [ ] **[REQ-EDU-ELAB-001]**: Elaboration is an ordered `education_course` step (explain-in-own-words).
- [ ] **[REQ-EDU-ELAB-002]**: Step complete writes Wiki artifact (templated) + ledger anchors.
- [ ] **[REQ-EDU-ELAB-003]**: Advances `current_step` / course status honestly (restart-safe).
- [ ] **[REQ-EDU-ELAB-004]**: Proof: failing test → green; Jarvis live smoke. No toast-only Done.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Construction / Application graded labs (CARD-324)
- Tutor agent runtime
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

- After scaffold → Jacob: **build** (or **build CARD-323**)
- After live OK → Jacob: **merge to qa**
