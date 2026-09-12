# [CARD-245] Education Construction (generative study artifacts)

> **Status**: In Review
> **Created**: 2026-09-11
> **Spec Reference**: Architect Done bar - Construction: Generative study artifacts -> Wiki only via matched wiki_note_*. Live proof: Note lands Inbox; no out-of-catalog tool death. Keep CARD-241 allowlist: wiki_note_* only; fail-soft; no wiki_overview kill.
> **Labels**: type:feature, P1, Education, Construction, AntiTheatre
> **Branch**: `feat/education-construction-245` (off `feat/education-elaboration-244` @ 7e0ef0d)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Jacob wants **Construction**: generate durable **study artifacts** (schema + dual-code outline + quiz/elaboration prompts) into **his Wiki** - not chat fluff.
2. Construction must land notes via catalog-matched **`wiki_note_*` only** (search/read/list/create[/append]) - same CARD-241 allowlist as Priming/Dual.
3. Live proof: a Construction note lands in **`00_Inbox/`**; Execute must **not** die on out-of-catalog tools (`wiki_overview` ERR kill is theatre / not Done).
4. Education Studio needs an operator path to Generate Construction artifacts (not chat-only).

### Beat 2: What AutoReiv Does Now
1. Priming / Dual Coding / Elaboration / Quiz paths exist; CARD-241 fail-soft allowlist covers Priming/Dual skills.
2. No Construction generative study-artifact engine that builds a multi-section study note and stages it via `wiki_note_create`.
3. No `education-construction` skill seed / Ask mode chip / Studio Construction panel.
4. Education skill expand markers only list priming + dual-coding (not construction).

### Beat 3: What Will Change
1. Construction engine: ground via `wiki_note_search`/`wiki_note_read` (fail soft), build generative study markdown, stage with `wiki_note_create` into `00_Inbox/`.
2. Seed `education-construction` skill + expand CARD-241 Education markers; Ask mode chip + Studio Generate path.
3. API `/api/education/construction/*` for deterministic generate (no wiki_overview).
4. Live smoke: note in Inbox; journey/tool path never depends on `wiki_overview`.

## 2. Acceptance Criteria (Architect locked)

- [x] **[REQ-EDU-CONST-001]**: Construction produces a generative study artifact (outline/schema + dual-code hooks + quiz/elaboration prompts) and stages it to Wiki **only** via catalog-matched `wiki_note_create` (plus optional search/read/list/append). **No `wiki_overview` / `wiki_graph`.**
- [x] **[REQ-EDU-CONST-002]**: Missing/blocked non-matched tools fail soft / skip so Construction still lands an Inbox note (reuse CARD-241 posture).
- [x] **[REQ-EDU-CONST-003]**: Education Studio operator path: Construction mode + Generate study artifact wired to `/api/education/construction/generate` (not chat-only theatre).
- [x] **[REQ-EDU-CONST-004]**: Live proof: note under `00_Inbox/`; smoke asserts no `wiki_overview` ERR death; feat off 244 tip only.
- [x] **Proof**: pytest + Studio vitest + `notes/marathon-card245-live-smoke.json`.

## 3. Constraints

- Continue marathon feat stack on `feat/education-construction-245` off 244 tip. Never qa/main. Do **not** merge to grok.
- Keep CARD-241 allowlist: `wiki_note_*` only; fail-soft; no wiki_overview kill.
- Reuse Wiki one-door Inbox staging. Do **not** invent a second corpus or tutor runtime.
- Chat still lists ticked tools every turn (AGENTS.md).
- TDD first (pytest and/or Studio vitest).
- Lumina / concept-player visuals remain OUT.
- Do **not** start CARD-246 in this task.

## 4. Out of scope (follow-on)

- Adaptive LLM-authored essay graders.
- Lumina / concept-player visuals.
- Multi-vault sync / PARA reorg beyond Inbox staging.
- CARD-246+.

## 5. Proof (when building)

- Pytest: construction uses only wiki_note_*; create lands Inbox; wiki_overview never called; fail-soft search still creates.
- Vitest / operator: Construction mode + panel wired to generate API.
- Live: notes/marathon-card245-live-smoke.json with Inbox note + no wiki_overview ERR.
