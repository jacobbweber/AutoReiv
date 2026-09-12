# [CARD-242] Education Retrieval + Retention (quiz + SRS)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Retrieval + Retention; quiz engine + binary external grade + mastery ledger in memory.db; 1-3-7-30 resurface via Routine -> standing Job; Education Studio path
> **Labels**: type:feature, P1, Education, Quiz, SRS, AntiTheatre
> **Branch**: `feat/education-retrieval-retention-242` (off `grok` @ 19f6e6b)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants **Retrieval + Retention** (quiz + SRS) so Education sticks - not one-shot Wiki notes that fade.
2. Priming / Dual Coding already land schema and dual-coded notes; without retrieval practice those notes do not become durable mastery.
3. Misses must resurface on a fixed schedule so review is automatic, not chat theatre.
4. Operator path lives in Education Studio (quiz / due reviews) - not "ask chat to quiz me" only.

### Beat 2: What AutoReiv Does Now
1. Education has Priming / Dual Coding Ask -> Wiki notes + standing Jobs (CARD-238..241).
2. No quiz engine, no SRS schedule, no durable mastery ledger in agent `memory.db`.
3. Wiki notes accumulate; nothing grades recall or schedules resurfacing after a miss.
4. Education Studio can mint teach Jobs and list them - no quiz / due-review surface.

### Beat 3: What Will Change
1. Quiz engine with **binary external grade** (not LLM self-score) over items derived from Wiki Priming / Dual Coding notes.
2. Durable **item x mastery ledger** in agent `memory.db` (item id, topic/path, grade, `next_due`).
3. Miss -> schedule resurface on fixed **1-3-7-30** driven by the mastery ledger; **Routine fires -> mints standing Job** for the due review (hard Architect Done bar).
4. Education Studio operator path for quiz / due reviews.
5. **Out of scope**: full personalized second-mind learner model (follow-on). Lumina visuals OUT.

---

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-RR-001]**: Durable mastery ledger in agent `memory.db` with at least item id, topic/path, grade, and `next_due`.
- [x] **[REQ-EDU-RR-002]**: Quiz items sourced from Wiki Priming / Dual Coding notes; grade is binary and **external** (not LLM self-score).
- [x] **[REQ-EDU-RR-003]**: On miss, schedule resurface at fixed **1-3-7-30** driven by the mastery ledger in `memory.db`. Resurface path **MUST** be **Routine -> standing Job** (reuse standing Job / Routine spine). **Chat-only reminder, toast, or "remind me later" is NOT Done** - rejected as theatre.
- [x] **[REQ-EDU-RR-004]**: Education Studio operator path for quiz / due list - not chat-only theatre.
- [x] **[REQ-EDU-RR-005]**: When a review is due, the **Routine fires and mints a standing Job** for that due review. Both are required for Done: (a) mastery ledger row with correct `next_due` on 1-3-7-30, and (b) the scheduler path **Routine -> standing Job** that surfaces the review. Missing either fails AC.
- [x] **Proof**: Miss an item -> ledger shows `next_due` -> Routine fires on schedule -> standing Job for due review is minted/surfaces. Feat off `grok` only; do not merge until asked. Chat toast / in-chat nudge alone does **not** satisfy Proof.

## 3. Constraints

- Feat off `grok` only. Never qa/main. Do not merge to grok unless asked.
- Reuse standing Job / Routine spine + agent `memory.db` (CARD-226); no second corpus or parallel orchestrator.
- Resurface after miss is **hard-locked**: Routine -> standing Job on 1-3-7-30 from mastery ledger. Chat-only reminder / toast is explicitly **not** Done.
- Binary external grade only - no same-model self-score theatre (align CARD-216 verifier posture).
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- No product code on this scaffold commit - Status **Ready** until Jacob says **build CARD-242**.

## 4. Out of scope (follow-on)

- Full personalized second-mind learner model.
- Lumina / concept-player visuals.
- Adaptive intervals beyond fixed 1-3-7-30.

## 5. Proof (when building)

- Pytest: mastery ledger write/read; miss schedules `next_due` on 1-3-7-30; external binary grade path (not LLM); Routine mint path creates standing Job for due review.
- Vitest / operator: Education Studio quiz + due list; miss -> later due review surfaces as standing Job (not chat toast).
- Live: miss one item -> `memory.db` row with `next_due` -> Routine fires -> standing Job for due review appears on schedule.
