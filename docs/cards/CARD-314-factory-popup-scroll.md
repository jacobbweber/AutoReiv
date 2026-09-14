# [CARD-314] Factory popup scroll + full studio window

> **Status**: In Review
> **Branch**: `feat/super-marathon-ui`
> **Created**: 2026-09-14

## Intent
Training Factory open/popup must not clip content — full usable studio window on desktop + phone scroll (same expand/scroll rule as Observe/Settings CARD-312/313). Deep-link from Agents still lands on **this agent’s** candidate queue (same durable store).

## Architect Done bars
- Training Factory open/popup must not clip content — full usable window on desktop + phone scroll
- Deep-link from Agents still lands on **this agent’s** candidate queue (same durable store)

## UX Done bars (locked)
- Factory open path presents as a **full studio window** (usable Factory Studio / large modal), **not** a clipped bottom-right toast/chip
- Body scrolls on phone **and** inside the desktop hosted window; nothing cut off below the fold (footer Launch/Cancel always reachable after scroll)
- Agents → Open Training Factory still scopes to **this agent’s** pending/candidate queue (`openFactoryStudioForAgent` + same durable store)

## Three Beats
1. **Means**: Open Training Factory / Train popup usable end-to-end on desktop + phone.
2. **Now**: Train modal clips; Factory studio may trap scroll without min-h-0 on hosted desktop; deep-link risk of toast-sized chrome.
3. **Change**: Scrollable modal chrome + Factory panel min-h-0 + full studio window sizing; preserve agent-scoped deep-link.

## Acceptance
- [x] `#trainAgentHandshakeModal` inner: `max-h-[90vh]` + `flex flex-col` + `min-h-0` + `overflow-hidden`; header/footer `flex-shrink-0`; body `flex-1 min-h-0 overflow-y-auto overscroll-contain`
- [x] HTML comment `CARD-314: Factory train modal scrolls`
- [x] `#view-factory` / `#factoryStudio` `min-h-0`; pipeline/runs keep inner scroll (outer overflow-hidden for runs split pane)
- [x] Desktop hosted Factory fills window (CSS CARD-314); dock defaultSize full studio (~960×680); tiny saved rects bumped on open
- [x] Agents → Open Training Factory / `openFactoryStudioForAgent` opens **full studio window**, not toast; still calls `setAgentScope` / loads that agent’s queue
- [x] Optional: `#labArtifactPreviewModal` scroll chrome hardened
- [x] Vitest `factory_popup_scroll_314.test.js`; `app.js?v=2.0.50`
- [x] CHANGELOG; do **not** merge qa/main; leave `uv.lock` dirty
