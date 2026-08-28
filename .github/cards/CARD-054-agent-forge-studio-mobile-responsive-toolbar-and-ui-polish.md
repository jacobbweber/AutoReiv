# [CARD-054] Agent Forge Studio Mobile Responsive Toolbar and UI Polish

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/agent-forge-mobile-responsive-toolbar/
> **Labels**: `type:bugfix`, `type:ui`, `milestone:18`

---

## 1. Why / Intent
Ensure the Agent Forge Studio header and action toolbar are fully responsive and legible across mobile and desktop devices. On mobile viewports, the action buttons (especially "Delete" and "Save Profile") were getting clipped horizontally off-screen. Additionally, the obsolete text badge "RPG Character Sheet" is removed to keep branding clean and professional.

---

## 2. What to Build
1. **Remove Obsolete Text Badge (`src/web/templates/index.html`)**:
   - Remove the `<span ...>RPG Character Sheet</span>` badge from the `#view-agents` header title.
2. **Mobile Responsive Toolbar Layout (`src/web/templates/index.html`)**:
   - Refactor the Agent Forge top toolbar into a responsive flex layout (`flex-col sm:flex-row gap-3`).
   - Group the agent select and action buttons (`#newAgentBtn`, `#saveAgentBtn`, `#deleteAgentBtn`) with `flex flex-wrap gap-2 w-full sm:w-auto items-center` so that all controls remain visible, wrap naturally, and are comfortably tap-friendly on narrow mobile screens (320px - 480px).
3. **Default-Collapsed Skill Packs (`src/web/static/modules/studios/forge.js`)**:
   - Skill pack tool item grids start in a collapsed state (`hidden`) by default with chevron rotated `-90deg` for a tidy, high-level overview.
4. **Automated Verification**:
   - Run Vitest, Playwright smoke tests, and preflight suite.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-MOB-001]`: Remove obsolete "RPG Character Sheet" badge from Agent Forge Studio in `src/web/templates/index.html`.
- [x] `[REQ-MOB-002]`: Agent Forge toolbar controls (select dropdown, New Agent, Save Profile, Delete) wrap responsively on mobile without horizontal clipping or overflow.
- [x] `[REQ-MOB-003]`: Skill pack tool grids in Agent Forge Studio are collapsed by default upon page navigation with interactive toggle to expand.
- [x] `[REQ-MOB-004]`: All automated tests (Pytest, Vitest, Playwright smoke suite, ESLint, Ruff) pass 100% green.

---

## 4. Constraints & Honor Flags
- Strict isolated `feat/agent-forge-mobile-toolbar` branch cut from `qa`.
- Zero regression on agent selection, saving, creation, or deletion functionality.

