# [CARD-237] Education Studio Shell (Wiki-backed ask + session list)

> **Status**: In Progress (P0 rail fix)
> **Created**: 2026-09-11
> **Spec Reference**: Education B lock; Architect slice: Studio shell after 236; Research ITS split
> **Labels**: type:feature, AutoReiv.Studio, Education
> **Branch**: `feat/education-studio-shell` (off `grok` @ d02dca0)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. A dedicated **Education Studio** - one surface to ask how he wants to be taught, grounded in **his Wiki**, not another Chat dump.
2. Outcome: knowledge moves **into his head** (durable understanding), tracked; Wiki stays the truth of *what exists*.
3. First visible slice is a **shell**: Wiki-backed topic ask + study-session list. Pedagogy (Learning OS 1-2) and visuals come later.
4. **Not this card**: 236 Job-mint, quiz/SRS, Lumina film, Mycel names/wiring, learner-model depth, amplifiers.

### Beat 2: What AutoReiv Does Now
1. Studios: Chat, Wiki, Forge, Observe, Routines - **no Education Studio** (pre-237).
2. Chat can write Wiki notes; standing Job mint path landed in CARD-236.
3. Shell reuses Chat standing Job mint + Wiki search; no second corpus.

### Beat 3: What Will Change
1. New Studio nav entry **Education** (same shell/theme as other Studios - sidebar + dock).
2. Wiki-backed ask: search notes + topic + "how to teach me" free prompt.
3. Session list: durable Education Jobs tied to `job_id` (Observe-filterable; Open in Chat).
4. Writes construction artifacts back to Wiki (existing wiki tools via standing Job). No second corpus.
5. Proof: open Education → ask on Wiki/topic → Job minted + session row + Observe `job_id`.

---

## 2. Acceptance Criteria (Architect locked bar)

- [x] **[REQ-EDU-SHELL-001]**: New Education Studio in the SPA rail (same shell pattern as other Studios).
- [x] **[REQ-EDU-SHELL-002]**: Wiki-backed ask box: topic + "how to teach me" → mints standing Job (236 path) with `success_rule`; shows copyable `job_id`.
- [x] **[REQ-EDU-SHELL-002a]**: Ask calls the same 236 standing mint path on a **fresh** Education session (never reuse Chat/phase `activeSessionId`); empty topic shows an error; SSE returns on `job_created` so the button cannot stick disabled. Proof: click -> `job_...` + Education Jobs row + Observe.
- [x] **[REQ-EDU-SHELL-003]**: Session list of Education Jobs (open in Chat/Observe).
- [x] **[REQ-EDU-SHELL-004]**: No quiz/SRS/visual player in this card — shell + Job mint only. Proof: ask from Education Studio → Wiki/note or park + Observe journey. Feat off `grok`.
- [x] **[REQ-EDU-SHELL-005]**: SPA rail/dock registry must load all existing Studios + Education; a single studio import/init failure must not blank `initApp` (isolate/fail that studio). Proof: Chat/Wiki/Observe/Education visible after hard-refresh; `app.js` parses (no stray brace); Education loaded via dynamic import.

---

## 3. Constraints

- Education B: Studio = interface only. Reuse Chat standing Job mint (236), Wiki tools, existing SPA patterns.
- Do NOT copy Mycel/Lumina module names or wiring.
- No Learning OS skills, quiz, SRS, concept-player, or learner-model depth in this card.
- Coordinate with existing Studios IA: add rail entry like others (sidebar nav + desktop dock).
- feat off `grok` only. Never qa/main.

## 4. Follow-on (not this card)

- 238+ Learning OS steps 1-2 (Priming + Dual Coding skills)
- Retrieval + Retention (quiz verifier + SRS routine → Job)
- Learner-model memory facts
- Visual amplifiers (concept-player / Lumina-style film) last

## 5. Proof

- Vitest: `education_studio.test.js` + dock registration in `agent_desktop.test.js` (includes REQ-005 isolation).
- Live smoke: `notes/marathon-card237-live-smoke.json` — Education-shaped ask minted `job_f23751949dad`; Observe standing-journey 200.
- **P0 2026-09-11**: stray `}` after prompts tab-loader aborted `app.js` parse (empty rail / no initApp). Fixed + Education dynamic-import for REQ-005.

- **P0 Ask mint 2026-09-11**: dead/hung Ask was reusing nested Chat phase session + waiting for full SSE; fixed fresh session + early job_created return.
