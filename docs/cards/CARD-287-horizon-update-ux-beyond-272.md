# [CARD-287] Horizon — update UX polish beyond CARD-272

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `ui`, `update`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. CARD-272 made install/Compose/update **honest**; UX of update flows still needs polish.

### Beat 2: What AutoReiv Does Now
1. Version API + honesty path shipped; operator update experience still basic.

### Beat 3: What Will Change
1. UX polish only — do not weaken 272 honesty contracts.
2. Studio path + empty/error/success states.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-287-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-287-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-287-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-287-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
