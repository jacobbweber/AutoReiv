# [CARD-139] Three-Surface Information Architecture and Streamlined Conversations Drawer

> **Status**: In Review
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
The mobile drawer and desktop sidebar previously displayed all 7 studios stacked in a single long vertical column above the conversation list. This caused severe vertical crowding, made accessing conversations difficult on mobile, and failed to deliver the promised consolidated 3-surface mental model (**Cockpit**, **Vault**, **Fleet**).

---

## 2. What to Build
1. **Three-Surface Switcher**:
   - Header / Mobile Surface Switcher (`#mobileSurfaceSwitcher`) with pills for **Cockpit** (`#surfaceBtnCockpit`), **Vault** (`#surfaceBtnVault`), and **Fleet** (`#surfaceBtnFleet`).
2. **Streamlined Conversations Drawer**:
   - Clean drawer layout prioritizing **+ New Chat** and the **Conversations List** (`#sessionList`), moving the 7 studio buttons into their respective surface contexts.
3. **Desktop Default Collapsed State**:
   - Sidebar `#sidebar` is hidden by default on desktop, giving Chat 100% viewport width unless toggled.
4. **Sub-Navigators for Vault & Fleet**:
   - Vault surface header with sub-tabs for **Wiki** (`#tab-wiki`) and **Projects** (`#tab-projects`).
   - Fleet surface header with sub-tabs for **Agents** (`#tab-agents`), **Routines** (`#tab-routines`), **Observability** (`#tab-observability`), and **Settings** (`#tab-settings`).
5. **Preservation of DOM Contracts**:
   - Retain all 7 tab buttons in the DOM to guarantee 100% parity with accessibility tests and route loaders.

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] `[REQ-SURFACE-001]` Consolidate navigation into 3 surfaces: Cockpit (Chat), Vault (Wiki, Projects), and Fleet (Agents, Routines, Observability, Settings).
- [ ] `[REQ-SURFACE-002]` Mobile drawer focuses on conversations with quick surface switching pills.
- [ ] `[REQ-SURFACE-003]` Desktop sidebar defaults to collapsed, expanding chat to maximum width.
- [ ] `[REQ-SURFACE-004]` Vault and Fleet provide top sub-tabs for their respective studios.
- [ ] `[REQ-SURFACE-005]` 100% of existing studio tab IDs (`#tab-chat`, `#tab-routines`, `#tab-observability`, `#tab-agents`, `#tab-settings`, `#tab-wiki`, `#tab-projects`) remain present and functional.
- [ ] Automated tests green via `npm run test:unit:frontend` and `pytest tests/unit/web`.
- [ ] Zero lint errors via `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
