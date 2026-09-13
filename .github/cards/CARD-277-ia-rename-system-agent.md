# [CARD-277] IA — rename AutoReiv-agent → System

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **B**.
> **Labels**: `type:chore`, `ui`, `track-b`, `ia`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. The platform agent labeled like a product peer confuses operators.
2. Rename to **System** in UI/IA — not a new runtime agent.

### Beat 2: What AutoReiv Does Now
1. Builtin / platform agent surfaces still say AutoReiv-agent (or similar) in places.
2. Architect: rename is IA, not a second control plane.

### Beat 3: What Will Change
1. Consistent **System** label in rail, Chat picker, Forge, Settings, docs strings.
2. No new agent id / no pack fork unless inventory proves a true id rename is required (call that out in Done bars).

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-277-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-277-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-277-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-277-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
