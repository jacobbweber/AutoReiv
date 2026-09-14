# [CARD-317] Education Learning OS — Priming write-back (Wiki + ledger anchors)

> **Status**: Ready
> **Created**: 2026-09-14
> **Branch**: `feat/education-priming-writeback` (off `qa` @ b9320d5)
> **Depends**: CARD-238 Priming/Dual skills + Ask modes; CARD-242/316 mastery ledger in `memory.db`
> **Labels**: type:feature, P0, Education, LearningOS, Priming, AntiTheatre

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Priming should leave **durable knowledge**, not only a chat Job that fades.
2. After Priming Ask, he wants a Wiki schema/outline note **and** ledger anchors for that topic in Education/`memory.db` so Retrieval can practice the same topic later.
3. Soft-fail if an unregistered wiki tool is called — the note must still land via catalog-matched `wiki_note_*` only.
4. No new Education chrome panels.

### Beat 2: What AutoReiv Does Now
1. CARD-238: Priming Ask mode + `education-priming` skill → standing Job → Wiki note via `wiki_note_*` (Done).
2. CARD-242/316: durable `education_mastery` + learner facts in agent `memory.db`; quiz extract can seed from Priming/Dual notes — but Priming Job success does not reliably **write ledger anchors** for the taught topic as part of write-back.
3. Education Ask Priming Done-when text expects a Wiki schema note; soft-fail / tool-policy behaviour for unregistered tools needs prove/harden so note still lands.

### Beat 3: What Will Change
1. Priming write-back path: standing Job / skill outcome writes (a) Wiki Priming schema/outline note and (b) **ledger anchors** for that topic in `memory.db` (`education_mastery` rows and/or equivalent learner anchors tied to `wiki_path` + topic).
2. Tools restricted to catalog-matched `wiki_note_search` / `wiki_note_list` / `wiki_note_read` / `wiki_note_create` (never `wiki_overview`); unregistered tools soft-fail without blocking note write-back.
3. Prove same topic visible in Wiki + `/api/education/learner` (or mastery list) after restart. No new Studio chrome.

## 2. Acceptance (Architect + Research locked)

- [ ] **[REQ-EDU-PRIM-001]**: Education Ask Priming → standing Job → Wiki note with schema/outline for the topic (catalog-matched `wiki_note_*` only).
- [ ] **[REQ-EDU-PRIM-002]**: Same success path writes **ledger anchors** for that topic in agent `memory.db` (item × mastery and/or learner facts with topic + `wiki_path`).
- [ ] **[REQ-EDU-PRIM-003]**: Unregistered / non-catalog wiki tools soft-fail so the Priming note still lands.
- [ ] **[REQ-EDU-PRIM-004]**: Proof: after restart, same topic shows in Wiki **and** learner/mastery API. Failing test → green; live smoke on Qwen Spark.
- [ ] **No new Education mastery/Priming chrome** (UX lock).

## 3. Constraints

- Branch `feat/education-priming-writeback` off `qa` only. Never merge `main` unless Jacob asks. Hold FF→`qa` until **merge to qa**.
- Extend CARD-238 + CARD-242/316 primitives — do not invent a second tutor runtime or parallel ledger.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- No product code on this scaffold commit — Status **Ready** until Jacob says **build**.

## 4. Out of scope

- Retrieval binary-grade deepen (next wave card)
- Retention Routine→Job polish (next wave)
- Dual Coding write-back deepen (follow-on unless needed for shared path)
- Amplifiers / Lumina / Observe brain panels

## 5. Wave order

1. This card — Priming write-back  
2. Retrieval binary external grade  
3. Retention Routine→Job  
Then capability-gap smoke; park amplifiers.

## 6. Reply phrases

- Scaffold done → Jacob: **build** (or **build CARD-317**)
- After live OK → Jacob: **merge to qa**
