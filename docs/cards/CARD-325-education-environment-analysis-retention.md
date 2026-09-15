# [CARD-325] Education Learning OS — Environment framing + Analysis→Retention handoff

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/card-325-education-environment-analysis-retention` (merged to qa)
> **Depends**: CARD-320+; CARD-319 Retention path on qa/main
> **Labels**: type:feature, P0, Education, LearningOS, Environment, Analysis, Retention, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Environment framing is part of the Learning OS course path (context for where/how learning applies).
2. Analysis → Retention handoff must be **hard** — kill/resume safe, durable, not a lost chat thread.
3. Restart / kill mid-handoff still leaves honest course + Retention schedule state.

### Beat 2: What AutoReiv Does Now
1. Retention Routine→Job (CARD-319) exists; Analysis and Environment framing are weaker / uneven in the course pipeline.
2. Handoff from Analysis into Retention can drop state on kill/resume.
3. Environment framing is not yet a clear durable course beat with Wiki/ledger anchors.

### Beat 3: What Will Change
1. Environment framing step / framing hooks in course path with durable write-back.
2. Harden Analysis→Retention handoff (kill/resume safe; same memory.db).
3. TDD + Jarvis live smoke proving resume after kill keeps course + Retention `next_due` honest.

---

## 2. Acceptance

- [x] **[REQ-EDU-ENV-001]**: Environment framing participates in the course path with durable Wiki/ledger anchors.
- [x] **[REQ-EDU-ENV-002]**: Analysis→Retention handoff is kill/resume safe (no lost schedule / course step).
- [x] **[REQ-EDU-ENV-003]**: Uses existing Retention `next_due` / Routine→Job primitives — no parallel scheduler.
- [x] **[REQ-EDU-ENV-004]**: Proof: failing test → green; Jarvis live smoke (kill mid-handoff → resume).

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Tutor agent (CARD-326)
- Adaptive depth / Studio chrome pass (CARD-327)
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

- After scaffold → Jacob: **build** (or **build CARD-325**)
- After live OK → Jacob: **merge to qa**
