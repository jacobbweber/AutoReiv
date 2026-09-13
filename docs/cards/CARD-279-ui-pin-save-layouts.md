# [CARD-279] UI — pin / save studio layouts

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **B**.
> **Labels**: `type:feature`, `ui`, `track-b`, `layout`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Operators want layouts that stick across sessions (pinned panes, saved arrangements).

### Beat 2: What AutoReiv Does Now
1. Layouts mostly reset; no durable per-operator layout prefs called out as a first-class feature.

### Beat 3: What Will Change
1. Durable layout prefs (settings or local store) + Studio path to pin/save/restore.
2. Proof: refresh / restart still restores pin.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-279-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-279-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-279-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-279-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
