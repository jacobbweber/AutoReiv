# [CARD-026] Mobile-First Responsive Layout and Sticky Viewport Overhaul

> **Status**: In Progress
> **Created**: 2026-08-23
> **Spec Reference**: `docs/specs/mobile-responsive/`
> **Labels**: `type:feature`, `milestone:26`, `domain:web`

---

## 1. Why / Intent
When accessing AutoReiv from mobile devices (smartphones and tablets):
1. Chat Studio causes the entire page to scroll on touch gestures, pushing the chat input bar off-screen instead of keeping it pinned firmly at the bottom with an independent scrolling message feed.
2. Multi-column studio views (Wiki Studio, System Info, Observability, Settings) force fixed desktop sidebar widths (`w-80`), resulting in squashed layouts and horizontal overflow.
3. Users require a seamless, responsive experience where screen width dynamically reorganizes UI components into mobile off-canvas drawers and full-width touch readers.

---

## 2. What to Build
1. **Dynamic Viewport Height & Sticky Chat Bottom Bar (`[REQ-RESP-001]`)**:
   - Update `<html>`, `<body>`, and `<main>` layout wrappers to enforce `h-screen h-[100dvh] overflow-hidden`.
   - In Chat Studio (`#view-chat`), isolate message scrolling to `#messagesContainer` (`flex-1 overflow-y-auto`) and anchor `#chatForm` in a sticky/pinned bottom container (`sticky bottom-0 z-20 flex-shrink-0`).
2. **Responsive Off-Canvas Drawers for Wiki Studio & System Info (`[REQ-RESP-002]`)**:
   - Convert Wiki Studio and System Info sidebars to responsive drawers (`hidden md:flex md:w-80` or slide-out drawer on `<md`) with mobile trigger buttons (`[📁 Vault]` / `[☰ Topics]`).
   - Selecting a note or topic on mobile automatically closes the drawer and focuses the full-width document workspace.
3. **Mobile-First Studio Grids, Modals & Mind Map Canvas (`[REQ-RESP-003]`)**:
   - Ensure Settings tables, Routines cards, Observability metric charts, and modals expand to full width on mobile viewports with touch drag/pinch-to-zoom support for the 2D Mind Map.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-RESP-001]`: Root viewport uses `100dvh` and Chat Studio retains sticky bottom input bar with independent message history scroll.
- [ ] `[REQ-RESP-002]`: Wiki Studio and System Info provide collapsible mobile drawers with quick toggle buttons that collapse upon item selection.
- [ ] `[REQ-RESP-003]`: Modals, Settings tables, and Mind Map canvas scale responsively to 100% viewport on mobile devices.
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.
- [ ] Pre-flight DoD passes via `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.

---

## 4. Constraints & Honor Flags
- Zero breaking changes to existing passing tests.
- Single isolated branch cut from `qa`.
