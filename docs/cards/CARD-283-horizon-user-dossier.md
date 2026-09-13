# [CARD-283] Horizon — user dossier

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `memory`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. A durable operator/user dossier the harness can use across agents (prefs, context, constraints).

### Beat 2: What AutoReiv Does Now
1. Memory.db / pinned memory exist per agent; no first-class cross-agent user dossier productized.

### Beat 3: What Will Change
1. Define storage vs memory boundary; Studio path; HITL for sensitive fields.
2. Anti-theatre: dossier must be readable/editable by operator, not a hidden prompt blob only.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-283-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-283-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-283-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-283-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
