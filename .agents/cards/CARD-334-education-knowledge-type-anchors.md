# [CARD-334] Education knowledge-type anchors

> **Status**: Done
> **Created**: 2026-09-14
> **Branch**: `feat/card-334-education-knowledge-type-anchors`
> **Depends**: Keep separate from CARD-324 Construction/Application; confirm specialization before build
> **Labels**: type:feature, P1, Education, LearningOS, KnowledgeTypes, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **concept vs tool vs method vs problem** get different teaching artifacts — not one generic course step shape.
2. Course steps specialize by knowledge type so learners see the right artifact shape.
3. Stays inside Education Learning OS / course pipeline honesty (Wiki + ledger where applicable).

### Beat 2: What AutoReiv Does Now
1. CARD-324 Construction/Application labs own graded lab pressure — different concern from knowledge-type shapes.
2. Course steps still risk one generic step chrome regardless of knowledge type.
3. No locked mapping of concept/tool/method/problem → distinct teaching artifacts.

### Beat 3: What Will Change
1. Knowledge-type anchors drive different teaching artifact shapes for concept / tool / method / problem.
2. Course-step specialization by knowledge type (confirm how with Architect before build).
3. TDD + Jarvis live smoke after specialization lock. **Do not implement until Needs discussion resolves.**

---

## 2. Acceptance

- [x] **[REQ-EDU-KTYPE-001]**: concept / tool / method / problem each have distinct teaching artifact shapes (not one generic step shape).
- [x] **[REQ-EDU-KTYPE-002]**: Course steps specialize by knowledge type per Architect lock.
- [x] **[REQ-EDU-KTYPE-003]**: Remains separate from CARD-324 Construction/Application graded labs (on purpose).
- [x] **[REQ-EDU-KTYPE-004]**: Proof: failing test → green; Jarvis live smoke. Labels include Education, LearningOS. No toast-only Done.

---

## 3. Needs discussion

**Overlap CARD-324 Construction/Application** — Resolved: Architect locked 4 distinct artifact shapes (`concept_brief`, `tool_reference`, `method_runbook`, `problem_scenario`) registered with Wiki templates (`education-concept`, `education-tool`, `education-method`, `education-problem`). Course steps specialize by knowledge type with explicit override support. CARD-324 graded labs retain objective test execution under pressure without interference.

---

## 4. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- **Do not implement** until Needs discussion (CARD-324 separation + specialization) is resolved.
- Do **not** change CARD-324 Status from this card's work.

---

## 5. Out of scope

- Construction / Application graded labs (CARD-324)
- Delivery profiles (CARD-333)
- Adaptive depth chrome (CARD-327)

---

## 6. Reply phrases

- After scaffold → Jacob: **build** (or **build CARD-334**) — only after Needs discussion resolves
- After live OK → Jacob: **merge to qa**
