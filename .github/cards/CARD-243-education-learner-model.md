# [CARD-243] Education Learner Model (strengths / weaknesses / patterns)

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Learner-model deepen; strengths/weaknesses/patterns in memory.db; quiz picks from weak items; kill/resume next Ask (or quiz set) pressures known miss, not random
> **Labels**: type:feature, P1, Education, LearnerModel, AntiTheatre
> **Branch**: eat/education-retrieval-retention-242 (continue marathon tip off CARD-242 @ ac0a1b4)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants a durable **second-mind learner model** so Education remembers what he is weak/strong at - not a thin grade ledger alone.
2. After a miss, the next quiz set / Ask must **pressure that known miss**, not shuffle random strong items.
3. Kill/resume (or restart serve) must still prefer the known miss from agent memory.db - no ephemeral in-process tutor state.
4. Build on CARD-242 mastery ledger; do **not** invent a second tutor runtime or parallel orchestrator.

### Beat 2: What AutoReiv Does Now
1. CARD-242 ships quiz engine + binary grade + ducation_mastery ledger + 1-3-7-30 + Routine->Job resurface.
2. Studio Extract Quiz loads items[0] (extraction order) - no weak/due preference.
3. No durable strengths/weaknesses/patterns facts beyond thin mastery rows.
4. Education Ask does not pressure known misses.

### Beat 3: What Will Change
1. On each quiz grade, write/update durable **learner-model facts** in agent memory.db (strengths / weaknesses / patterns) via semantic facts adjacent to the mastery ledger.
2. Quiz selection API prefers **due -> weak/missed -> unseen** over random / first-extracted.
3. Education Ask (and Studio Next Quiz) can pressure a known miss from the learner model.
4. Live proof: miss -> kill/resume serve -> next quiz/Ask still targets that miss.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-LM-001]**: Strengths / weaknesses / patterns from quiz grades persist in agent memory.db (extend mastery and/or adjacent semantic facts). Never storage.db.
- [x] **[REQ-EDU-LM-002]**: Quiz selection prefers weak / due / missed items over random or first-extracted-only order when those exist.
- [x] **[REQ-EDU-LM-003]**: Next Education Ask (or quiz set) can pressure a known miss from the learner model - not a random strong item when a miss is known.
- [x] **[REQ-EDU-LM-004]**: Kill/resume or restart serve: next quiz/Ask still pressures the known miss (durable memory.db, no in-process-only tutor state).
- [x] **Proof**: Miss an item -> learner weakness fact + mastery row in memory.db -> restart serve -> /api/education/quiz/next (or Ask) returns that miss ahead of strong/random items.

## 3. Constraints

- Continue marathon feat stack on eat/education-retrieval-retention-242 (or split eat/education-learner-model-243 only if cleaner). Never qa/main. Do **not** merge to grok.
- Thin ledger (242) -> durable second-mind facts; **do not invent a second tutor runtime**.
- Reuse agent memory.db / AgentMemoryRepository (CARD-116/226/242).
- Binary external grade remains the only scorer (no LLM self-score theatre).
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Lumina / concept-player visuals remain OUT.
- Do **not** start CARD-244 in this task.

## 4. Out of scope (follow-on)

- Adaptive SRS beyond fixed 1-3-7-30.
- Full multi-learner profiles / cross-agent transfer.
- Lumina / concept-player visuals.
- CARD-244+.

## 5. Proof (when building)

- Pytest: grade miss writes weakness/pattern facts; select_quiz prefers due/weak over strong; reopen AgentMemoryRepository (simulating restart) still returns the miss first.
- Vitest / operator: Studio Next Quiz uses weak-preferring endpoint (not items[0] only).
- Live: miss -> peek memory.db learner facts -> kill/resume serve -> quiz/next pressures known miss; notes in 
otes/marathon-card243-live-smoke.json.
---
