# [CARD-237] Education Studio Shell (Wiki-backed ask + session list)

> **Status**: Ready (blocked on CARD-236 Done)
> **Created**: 2026-09-11
> **Spec Reference**: Education B lock; Architect slice: Studio shell after 236; Research ITS split
> **Labels**: type:feature, AutoReiv.Studio, Education

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. A dedicated **Education Studio** — one surface to ask how he wants to be taught, grounded in **his Wiki**, not another Chat dump.
2. Outcome: knowledge moves **into his head** (durable understanding), tracked; Wiki stays the truth of *what exists*.
3. First visible slice is a **shell**: Wiki-backed topic ask + study-session list. Pedagogy (Learning OS 1–2) and visuals come later.
4. **Not this card**: 236 Job-mint, quiz/SRS, Lumina film, Mycel names/wiring, learner-model depth, amplifiers.

### Beat 2: What AutoReiv Does Now
1. Studios: Chat, Wiki, Forge, Observe, Routines — **no Education Studio**.
2. Chat can write Wiki notes; no study session object, no learner-facing spine.
3. Jobs exist but Chat outcome asks often skip minting (236). Shell must mint Jobs once 236 is Done.

### Beat 3: What Will Change
1. New Studio nav entry **Education** (same shell/theme as other Studios — coordinate IA with UI/UX if needed).
2. Wiki-backed ask: pick/search notes + free prompt (“explain X like … / ADHD bite-size”).
3. Session list: durable study sessions tied to `job_id` (Observe-filterable).
4. Writes construction artifacts back to Wiki (existing wiki tools). No second corpus.
5. Proof: open Education → ask on an existing Wiki note → Job minted + session row + Observe `job_id`. Blocked until 236 green.

---

## 2. Acceptance Criteria (draft — Architect sharpen when 236 lands)

- [ ] **[REQ-EDUSHELL-001]**: Education Studio in Studio nav; Wiki-backed ask + session list.
- [ ] **[REQ-EDUSHELL-002]**: Ask creates standing Job (`job_id` in strip + Observe) — depends 236.
- [ ] **[REQ-EDUSHELL-003]**: Construction writes to Wiki only (no parallel notes DB).
- [ ] **[REQ-EDUSHELL-004]**: No visual amplifier / quiz engine in this card.
- [ ] **[REQ-EDUSHELL-005]**: Red→green + operator walk; feat off `grok` only. Never qa/main.

---

## 3. Constraints

- Education B: pedagogy pack skills + Jobs; Studio = interface. Learner model later in `memory.db`.
- Do not copy Mycel/Grok/Lumina primitives or module names.
- Hold implement until 236 Done **and** Jacob **build** on this card.

## 4. Follow-on (not this card)

- 238+ Learning OS steps 1–2 (Priming + Dual Coding skills)
- Retrieval + Retention (quiz verifier + SRS routine → Job)
- Learner-model memory facts
- Visual amplifiers (concept-player / Lumina-style film) last
