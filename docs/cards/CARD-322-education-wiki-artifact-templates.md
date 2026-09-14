# [CARD-322] Education Learning OS — Wiki templates for every Education artifact

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-studio-finish`
> **Depends**: CARD-320 / CARD-321 write-back paths
> **Labels**: type:feature, P0, Education, LearningOS, Wiki, Templates, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Every Education activity (notes, quizzes, flashcards, labs, scores) must use **enforced Wiki templates** + front matter.
2. No freeform dump into Wiki — artifacts are tagged and structured so later steps / Tutor can find them.
3. Create/update paths require a real `template_id` / tag, not optional theatre.

### Beat 2: What AutoReiv Does Now
1. Wiki templates exist unevenly across the product.
2. Education write-backs (Priming / Retrieval / course steps) do **not** guarantee consistent template tagging + front matter.
3. Downstream consumers cannot reliably filter Education artifacts by type.

### Beat 3: What Will Change
1. Template catalog for Education artifacts (notes, quizzes, flashcards, labs, scores).
2. Create/update paths require `template_id` / tag; reject or soft-route freeform dumps.
3. Proof in Wiki front matter after Priming / Retrieval / course steps.

---

## 2. Acceptance

- [ ] **[REQ-EDU-WIKI-TPL-001]**: Catalog of Wiki templates covering Education notes, quizzes, flashcards, labs, scores.
- [ ] **[REQ-EDU-WIKI-TPL-002]**: Education create/update write-back paths require `template_id` / template tag + front matter.
- [ ] **[REQ-EDU-WIKI-TPL-003]**: No freeform Education dump path that bypasses templates.
- [ ] **[REQ-EDU-WIKI-TPL-004]**: Proof: after Priming / Retrieval / course steps, Wiki notes show expected template front matter. TDD + Jarvis smoke.

---

## 3. Constraints

- Branch `feat/education-studio-finish`. Never merge `main` unless Jacob asks. **Hold FF→`qa` until Jacob says merge to qa.**
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Same `memory.db` brain — never invent a second tutor / education storage.db.
- Do **not** change CARD-320 Status from this card's work.


## 4. Out of scope

- Tutor agent runtime (CARD-326)
- Amplifiers / Lumina
- Inventing a second Wiki store outside existing wiki tools

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

- After scaffold → Jacob: **build** (or **build CARD-322**)
- After live OK → Jacob: **merge to qa**
