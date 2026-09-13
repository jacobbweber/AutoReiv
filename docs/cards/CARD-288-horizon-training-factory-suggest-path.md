# [CARD-288] Horizon — Training Factory tool-fix suggest path

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `training-factory`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. On-the-fly tool-fix suggest path must be truth vs theatre (gaps → train → real candidate, not toast-only).
2. Builds on CARD-270 honesty.

### Beat 2: What AutoReiv Does Now
1. CARD-270 landed Training Factory truth (train→training; empty promote = honest can’t).
2. Suggest-from-gap → operator-visible candidate path still thin / horizon.

### Beat 3: What Will Change
1. Durable gap→candidate loop + Forge/Studio path + failing then green proof.
2. No fake “trained” status.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-288-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-288-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-288-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-288-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
