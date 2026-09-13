# [CARD-282] Horizon — LLM journey telemetry + token accuracy

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `telemetry`, `observability`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. See token/journey truth for long Jobs — not marketing counters.
2. Open questions: telemetry DB wipe policy; lifetime totals vs session totals.

### Beat 2: What AutoReiv Does Now
1. Observability / journey events exist; token accuracy and lifetime accounting still soft.

### Beat 3: What Will Change
1. Durable telemetry model + Studio path + accuracy proof vs provider usage.
2. Document wipe/lifetime policy as AC, not a separate product card unless scope explodes.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-282-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-282-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-282-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-282-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
