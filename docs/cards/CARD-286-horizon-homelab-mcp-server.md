# [CARD-286] Horizon — Homelab MCP server

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Parent epic CARD-275 (B/D backlog capture). Track **D**.
> **Labels**: `type:feature`, `horizon`, `track-d`, `homelab`, `mcp`
> **Branch**: `feat/backlog-bd-capture-275` off `qa` (scaffold only)
> **Build**: **Do not build** until Architect locks Done bars (and Jacob unlocks if Track D).

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Homelab outcomes need an MCP server the harness can drive (illustrative domain, not hardwired product).
2. Example class: Windows domain / file servers — generalize.

### Beat 2: What AutoReiv Does Now
1. Homelab agents/packs exist; dedicated Homelab MCP server not a captured Ready epic.

### Beat 3: What Will Change
1. Server scope, tools, HITL for destructive ops, Studio mount path, live proof on LAN.
2. Do not hardwire Homelab into kernel — pack/MCP boundary.

---

## 2. Acceptance Criteria (placeholders — Architect locks before build)

- [ ] **[REQ-286-001]**: Durable state named (DB / settings / files).
- [ ] **[REQ-286-002]**: Studio / operator path named (route or surface).
- [ ] **[REQ-286-003]**: Failure modes + proof (test or live path) named in Done bars.
- [ ] **[REQ-286-004]**: Anti-theatre: no UI-only fake of the capability.

---

## 3. Constraints

- Parent: CARD-275. Skip re-carding 268–274.
- Surface/IA work must not fork Job / HITL / Observe spines.
- Track D remains parked until Jacob unlocks.
