# [CARD-276] UI — studio nav + consolidate duplicate levers

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **B**.
> **Labels**: `type:feature`, `ui`, `track-b`, `studio-nav`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. One studio at a time, but duplicate levers across studios should consolidate as we go.
2. Navigation should match real operator jobs: monitor, decide, hand off, act.

### Beat 2: What AutoReiv Does Now
1. Rail + many studios exist; some capabilities appear in more than one place.
2. UI marathon paused for CARD-274; tip is clean on `qa` @ 2541c3a.

### Beat 3: What Will Change
1. UX proposes IA/nav order; Architect Done bars; Builder implements per studio cards.
2. Consolidate only when levers truly duplicate — document moves in this card / epic index.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-276-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-276-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-276-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-276-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
