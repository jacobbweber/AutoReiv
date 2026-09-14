# [CARD-328] Education Learning OS — Amplifiers / Lumina polish (LAST)

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: CARD-321–327 Done preferred
> **Labels**: type:feature, P2, Education, LearningOS, Amplifiers, Lumina, Polish, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Amplifiers (Lumina-style) polish only **AFTER** core Learning OS course path is real.
2. Honest wiring to existing ledger / course state — no fake autonomy.
3. Lower priority / P2 — park until 321–327 land.

### Beat 2: What AutoReiv Does Now
1. Amplifiers parked repeatedly; not on the critical path.
2. Core course path (320+) must finish before amplifier chrome is trustworthy.
3. Risk of amplifier theatre that pretends autonomy without ledger truth.

### Beat 3: What Will Change
1. Amplifier surfaces wired honestly to existing ledger / course state.
2. No fake autonomy; no parallel brain.
3. Polish only — TDD where behaviour is asserted; Jarvis smoke optional but honest.

---

## 2. Acceptance

- [ ] **[REQ-EDU-AMP-001]**: Amplifier / Lumina surfaces wire to existing `education_course` + mastery ledger state.
- [ ] **[REQ-EDU-AMP-002]**: No fake autonomy / no second storage brain.
- [ ] **[REQ-EDU-AMP-003]**: Lands only after core Learning OS course path (321–327 preferred Done).
- [ ] **[REQ-EDU-AMP-004]**: Proof: honest demo or smoke; no toast-only “amplified” Done.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Replacing course pipeline
- Adaptive depth / Tutor core work (those are earlier cards)
- Shipping amplifiers before CARD-321–327

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

- After scaffold → Jacob: **build** (or **build CARD-328**)
- After live OK → Jacob: **merge to qa**
