# [CARD-278] UI — Education Studio overhaul

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **B**.
> **Labels**: `type:feature`, `ui`, `track-b`, `education`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Education matters personally (burnout risk); shell/IA should feel like a learning OS, not a bolted panel.
2. Overhaul surface/layout — do not rip out 242–250 runtime (ledger, SRS, learner model).

### Beat 2: What AutoReiv Does Now
1. Education Studio shell + viewport (237–250) exist; chrome still early vs Chat/Observe.
2. Lumina parked as Dual Coding amplifier epic (CARD-281), not this card.

### Beat 3: What Will Change
1. UX IA + wireframes for Education; consolidate overlapping Learn/Practice chrome if any.
2. Keep memory.db ledger / Routine→Job resurface contracts intact.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-278-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-278-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-278-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-278-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
