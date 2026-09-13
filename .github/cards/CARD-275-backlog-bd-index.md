# [CARD-275] Backlog capture — Track B (UI marathon) + Track D (horizon)

> **Status**: Ready
> **Created**: 2026-09-13
> **Spec Reference**: Design-room 2026-09-13 — Jacob dump was track-sorted in memory, not repo cards. Architect ask: capture B/D before UI dig-in. Research adds Training Factory suggest-path + visual DAG canvas.
> **Labels**: `type:docs`, `backlog`, `track-b`, `track-d`
> **Branch**: `feat/backlog-bd-capture-275` off `qa`
> **Build**: **No build** — index + child Ready stubs only. Skip re-carding 268–274.

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. Awhile back he listed many features for after the foundation pass. Those lived in Design chat memory as tracks A→D, not as durable repo cards.
2. Before the UI marathon dig-in, capture that backlog in `.github/cards` so nothing is lost.
3. Tracks A (Observe) and C (foundation audit 268–272 + 274 vLLM) are **done** — do not re-card them.

### Beat 2: What AutoReiv Does Now
1. `steering/roadmap.md` is milestone-oriented and does not list Jacob’s B/D dump as Ready cards.
2. Education (242–250) and bones (260–266) cards exist; Lumina/horizon items were explicitly **parked**.
3. Chat memory ≠ backlog — Architect/Research confirmed the gap.

### Beat 3: What Will Change
1. This epic indexes Track **B** (UI marathon) and Track **D** (horizon) as child Ready cards 276–286.
2. Child cards stay **Ready / parked for build** until UX proposes studio order and Architect locks Done bars (B), or Jacob unlocks horizon (D).
3. Consolidations during the UI marathon may close or merge child cards — update this index when that happens.

---

## 2. Acceptance Criteria

- [x] **[REQ-BACKLOG-275-001]**: Epic index exists on a feat off `qa`.
- [x] **[REQ-BACKLOG-275-002]**: Child Ready cards cover Architect B list + D list + Research extras (Training Factory suggest-path, visual DAG/canvas).
- [x] **[REQ-BACKLOG-275-003]**: No re-card of 268–274; no product code / no serve change in this feat.
- [ ] **[REQ-BACKLOG-275-004]**: FF into `qa` when Jacob says merge (docs-only).

---

## 3. Child card map

### Track B — UI marathon (surface only; order TBD by UX)
| Card | Topic |
|------|--------|
| CARD-276 | Studio nav + consolidate duplicate levers |
| CARD-277 | Rename AutoReiv-agent → **System** (IA only) |
| CARD-278 | Education Studio overhaul (shell/IA; not re-open 242–250 runtime) |
| CARD-279 | Pin / save studio layouts |
| CARD-280 | In-app doc viewers |

### Track D — Horizon (parked until Jacob unlocks)
| Card | Topic |
|------|--------|
| CARD-281 | Lumina (concept→metaphor film / Dual Coding amplifier) |
| CARD-282 | LLM journey telemetry + token accuracy (incl. DB wipe / lifetime totals as open Qs) |
| CARD-283 | User dossier |
| CARD-284 | Feature-request → GitHub issue |
| CARD-285 | Plugins / integrations surface |
| CARD-286 | Homelab MCP server |
| CARD-287 | Update UX polish beyond CARD-272 honesty |
| CARD-288 | Training Factory / on-the-fly tool-fix suggest path (truth vs theatre) |
| CARD-289 | Visual DAG / long-workflow canvas (pack vs skill vs Studio — open) |

---

## 4. Constraints

- Feats off `qa` only.
- No Job-spine reopen; UI = surface/IA.
- Horizon stays parked; scaffolding ≠ unlock.
