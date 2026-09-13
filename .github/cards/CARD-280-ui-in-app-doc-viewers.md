# [CARD-280] UI — in-app doc viewers

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **B**.
> **Labels**: `type:feature`, `ui`, `track-b`, `docs-viewer`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Read docs / notes / specs inside the app without bouncing to an external editor for every glance.

### Beat 2: What AutoReiv Does Now
1. Wiki Studio and some markdown paths exist; general in-app viewers for repo/docs are incomplete or fragmented.

### Beat 3: What Will Change
1. Viewer surface(s) with clear scope (wiki vs repo vs shipped docs) + UX Done bars.
2. Must not fake “open” without real file content.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-280-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-280-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-280-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-280-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
