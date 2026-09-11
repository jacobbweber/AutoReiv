# [CARD-236] Chat Outcome Ask Always Mints Standing Job + Observe job_id

> **Status**: Done
> **Created**: 2026-09-11
> **Spec Reference**: CARD-230 outcome intake; CARD-227 standing journey; wave-2 eval gap (`notes/marathon-wave2-operator-eval-2026-09-11.md`)
> **Labels**: type:bug, type:architecture, AutoReiv.Orchestration, AntiTheatre, Education-prereq

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. When he asks Chat to **do something real** (write a Wiki note, a study Job, a health check with a done-when), AutoReiv must treat that as a **Job** he can replay — not a one-off Chat reply that vanishes from Observability.
2. He walked CoS prompt #2 (Wiki note with a done-when): the note appeared and felt right, but **Observe had no `job_id`**. That is theatre for the standing spine Education Studio will sit on.
3. Short chitchat must stay a normal reply (no Job).
4. **Not this card**: Education Studio UI, SRS, visuals, 237+ shell.

### Beat 2: What AutoReiv Does Now
1. CARD-230 intake exists (outcome-shaped → Job + `success_rule` + matched IDs) and unit/live smokes passed **in-process**.
2. Operator walk 2026-09-11 session `44bf694d-ee1c-4726-954a-658e543a3b35`: ask #2 used `wiki_note_create` ReAct; Chat journey `jobs: []`; no Job row on live `%LOCALAPPDATA%\AutoReiv` for that session.
3. Ask #4 failed via `handoff_to_agent` + `cli_exec`, not standing verifier replan/park.
4. Live data dir is `%LOCALAPPDATA%\AutoReiv\`, not repo `data/`.

### Beat 3: What Will Change
1. Chat standing path: **outcome-shaped ask always mints a durable Job** before the first tool/phase that fulfills the outcome — including Wiki-write asks.
2. Chat Job strip + Observability `/api/observability/standing-journey?job_id=` show intake → phases.
3. Classifier: short chitchat remains ReAct; outcome / deliverable / done-when language always Jobs.
4. Proof: operator #2-style Wiki ask → note exists **and** Observe `job_id` non-empty. `jobs=[]` after a successful outcome reply = fail.

---

## 2. Acceptance Criteria (Definition of Done) — Architect locked

- [x] **[REQ-JOBMINT-001]**: Outcome-shaped Chat ask (230) always creates a durable Job before phase 1 — never `jobs=[]` after a successful outcome reply.
- [x] **[REQ-JOBMINT-002]**: Chat Job strip + Observability filter by that `job_id` show intake → phases (journey spans).
- [x] **[REQ-JOBMINT-003]**: Short chitchat still plain ReAct (no Job).
- [x] **[REQ-JOBMINT-004]**: Operator proof: CoS #2-style Wiki ask → note + real `job_id` in Observe. Red→green + live walk; feat off `grok` only.

---

## 3. Constraints & Honor Flags

- Branch: `feat/education-studio-236` (off `grok`). Never qa/main.
- Hold **implement until Jacob says build**.
- Anti-theatre: Education Studio must not ship until this gap is closed (Architect B).
- Out of scope: Education shell (237), Learning OS skills, Lumina/Mycel copy, visual amplifiers.

## 4. Modules Likely Touched (when build)

- `src/application/orchestration/outcome_intake.py`
- `src/web/routers/chat.py` (standing Chat path vs ReAct bypass)
- Observability standing journey + Chat Job strip
- Tests covering live Chat stream → Job row for Wiki-create outcome asks

## 5. Live data note

Operator proof uses `%LOCALAPPDATA%\AutoReiv\database\autoreiv.db` (restart serve after pull).

---

## Live proof (2026-09-11)

- Session: `197a9053-ef44-4485-b504-5fed86690f8f`
- `job_id`: `job_0dd0685b3f0c`
- Wiki note: `00_Inbox/card_236_job_mint_in_autoreiv.md` (uid `20260911-130703`)
- Observe standing-journey: timeline/spans non-empty for that `job_id`
- Artifact: `notes/marathon-card236-live-smoke.json`
