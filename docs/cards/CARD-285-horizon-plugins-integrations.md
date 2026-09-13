# [CARD-285] Horizon — plugins / integrations surface

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `plugins`, `mcp`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. A clear home for plugins/integrations beyond ad-hoc MCP toggles.

### Beat 2: What AutoReiv Does Now
1. MCP client/settings exist; “plugins” as operator IA is incomplete.

### Beat 3: What Will Change
1. IA + registry surface; trust/HITL; no second tool protocol.
2. Coordinate with Homelab MCP (CARD-286) so we don’t double-build.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-285-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-285-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-285-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-285-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
