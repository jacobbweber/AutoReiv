# [CARD-246] Education Application (Exercise Job + binary verify)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Application: Exercise Job + binary verify (not self-grade). Live: Fail parks / replan; pass advances mastery. Research: binary external verify + Wiki/memory.db write-back.
> **Labels**: type:feature, P1, Education, Application, AntiTheatre
> **Branch**: `feat/education-application-246` (off `feat/education-construction-245` @ ac2adf4)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants **Application**: real **exercise Jobs** where the learner applies knowledge - not another chat quiz fluff loop.
2. The grade must be a **binary external verify** against a reference / required-concepts rubric - **LLM self-score is theatre and not Done**.
3. Live: a **fail parks or bounded-replans** (reuse CARD-232 HITL park / replan<=3); a **pass advances the mastery ledger**.
4. Live proof must show **Wiki and/or memory.db write-back** of the application outcome (durable second-mind).

### Beat 2: What AutoReiv Does Now
1. CARD-242..245 ship quiz/elaboration binary grade + mastery ledger + Routine->Job SRS + Construction artifacts + Studio panels.
2. No Application / Exercise surface that prefers minting a **standing Exercise Job** and wires fail -> park/replan.
3. No application outcome write-back beyond quiz/elaboration grades.
4. Education Studio has Quiz / Elaboration / Construction - no Application operator path.

### Beat 3: What Will Change
1. Application engine: extract Exercise/Application tasks from Wiki; grade with **binary external** check (no LLM).
2. Prefer standing **Exercise Job** mint (catalog resolve) where natural; reuse Job / HITL / mastery / SRS primitives.
3. Fail -> bounded auto-replan or HITL park (CARD-232) and/or ledger miss + resurface; Pass -> advance mastery ledger.
4. Wiki + memory.db write-back; Education Studio Application panel + `/api/education/application/*`.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-APP-001]**: Application exercise items sourced from Wiki (`## Application` / `## Exercise`); grade is **binary external** via reference equality/containment **or** required-concepts rubric. **LLM self-score is not Done**.
- [x] **[REQ-EDU-APP-002]**: Prefer standing **Exercise Job** mint for exercises; fail path uses **bounded replan or HITL park** (reuse CARD-232) and updates mastery ledger (`grade=miss`, `next_due` on 1-3-7-30) so retention can resurface. Chat toast alone is not Done.
- [x] **[REQ-EDU-APP-003]**: Pass advances the mastery ledger (`grade=pass`, interval stage advances). Application outcome write-back lands in Wiki and/or agent `memory.db` (never `storage.db`).
- [x] **[REQ-EDU-APP-004]**: Education Studio operator path for Application (extract / mint Exercise Job / submit attempt / binary grade) - not chat-only theatre.
- [x] **Proof**: pytest + Studio path + `notes/marathon-card246-live-smoke.json` with fail->park/replan evidence and pass->mastery advance + Wiki/memory write-back.

## 3. Constraints

- Continue marathon feat stack on `feat/education-application-246` off 245 tip. Never qa/main. Do **not** merge to grok.
- Reuse Job / HITL / mastery / SRS / bounded replan primitives. Do **not** invent a second tutor runtime.
- Binary external grade only - no same-model self-score theatre.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Lumina / concept-player visuals remain OUT.
- Do **not** start CARD-247 in this task.

## 4. Out of scope (follow-on)

- Adaptive free-form semantic / embedding graders as primary score.
- Multi-step coding sandboxes beyond binary external verify.
- Lumina / concept-player visuals.
- CARD-247+.

## 5. Proof (when building)

- Pytest: binary grade (no LLM); fail -> replan/park or resurface Job + ledger miss; pass advances mastery; Wiki/memory write-back; Exercise Job mint.
- Studio: Application panel wired to `/api/education/application/*`.
- Live: notes/marathon-card246-live-smoke.json.
