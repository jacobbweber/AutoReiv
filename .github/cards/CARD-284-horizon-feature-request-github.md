# [CARD-284] Horizon — feature-request → GitHub issue

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `github`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. From inside AutoReiv, turn a feature ask into a tracked GitHub issue.

### Beat 2: What AutoReiv Does Now
1. No first-class “file issue from Studio” loop called out as shipped.

### Beat 3: What Will Change
1. Operator path + auth/credential policy + proof issue created on jacobbweber/AutoReiv (or configured repo).
2. HITL before publish.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-284-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-284-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-284-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-284-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
