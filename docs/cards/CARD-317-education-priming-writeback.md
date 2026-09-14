# [CARD-317] Education Learning OS — Priming write-back (Wiki + ledger anchors)

> **Status**: In Review
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

- [x] **[REQ-EDU-PRIM-001]**: Education Ask Priming → standing Job → Wiki note with schema/outline for the topic (catalog-matched `wiki_note_*` only).
- [x] **[REQ-EDU-PRIM-002]**: Same success path writes **ledger anchors** for that topic in agent `memory.db` (item × mastery and/or learner facts with topic + `wiki_path`).
- [x] **[REQ-EDU-PRIM-003]**: Unregistered / non-catalog wiki tools soft-fail so the Priming note still lands.
- [x] **[REQ-EDU-PRIM-004]**: Proof: after restart, same topic shows in Wiki **and** learner/mastery API. Failing test → green; live smoke on Qwen Spark.
- [x] **No new Education mastery/Priming chrome** (UX lock).

## 3. Constraints

- Branch `feat/education-priming-writeback` off `qa` only. Never merge `main` unless Jacob asks. Hold FF→`qa` until **merge to qa**.
- Extend CARD-238 + CARD-242/316 primitives — do not invent a second tutor runtime or parallel ledger.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first. Leave `uv.lock` dirty/uncommitted.
- Built after Jacob **build**; Status **In Review** pending live OK + merge to qa.

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


## 7. Executor proof (CARD-317)

### Gaps found
1. Priming Ask / skill landed Wiki notes but did **not** reliably write `education_mastery` / learner anchors for the taught topic as part of write-back — **fixed** via `priming_writeback` + API.
2. Soft-fail for unregistered/forbidden wiki tools already in tool-policy gate (CARD-241); Priming write-back path now proves soft-fail does not block note+ledger success.
3. No new Education chrome (UX lock held).

### Files
- `src/application/education/priming.py` — write-back helper (schema note + ledger seed + soft-fail)
- `src/web/routers/education.py` — `POST /api/education/priming/writeback` + ask-clause; Priming Ask Done-when includes ledger
- `src/application/skills/wiki_tools.py` — best-effort Priming tag hook (requires `AUTOREIV_DATA_DIR`)
- `src/infrastructure/skills/seeds/education-priming/SKILL.md` — ledger Done-when
- `tests/unit/education/test_card317_priming_writeback.py` — TDD
- `CHANGELOG.md` — Unreleased CARD-317

### Pytest
`tests/unit/education/test_card317_priming_writeback.py` (+ CARD-241 soft-fail) green.

### Live smoke
`POST /api/education/priming/writeback` → Wiki `00_Inbox/` note + mastery/learner; `restart_serve.py --port 8000` → same topic still present.
