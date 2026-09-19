# Requirements Specification: Agent Forge Studio Mobile Responsive Toolbar and UI Polish

## 1. System Intent & Scope
Enhance Agent Forge Studio (`#view-agents`) by making the top toolbar layout fluidly responsive across mobile viewports, removing the obsolete `"RPG Character Sheet"` badge text from the title, and setting skill packs to be collapsed by default for an organized high-level overview.

---

## 2. EARS Requirements Matrix

### [REQ-MOB-001] Removal of RPG Character Sheet Badge Text
- **Type**: Ubiquitous
- **Description**: The AutoReiv Web SPA SHALL not render the text `"RPG Character Sheet"` within the Agent Forge header in `src/web/templates/index.html`.
- **Acceptance Criteria**:
  1. The badge containing `"RPG Character Sheet"` is removed from `#view-agents`.
  2. The title cleanly displays `"Agent Forge Studio"`.

### [REQ-MOB-002] Mobile Responsive Wrapping Toolbar
- **Type**: Ubiquitous
- **Description**: The Agent Forge top toolbar SHALL wrap its controls responsively on mobile viewports ($\le 480\text{px}$) so that all buttons (`#newAgentBtn`, `#saveAgentBtn`, `#deleteAgentBtn`) and `#forgeAgentSelect` remain fully visible, accessible, and not clipped off-screen.
- **Acceptance Criteria**:
  1. The toolbar flex layout wraps cleanly (`flex-col sm:flex-row gap-3`).
  2. The select dropdown and buttons adjust width and wrap without horizontal scroll or viewport overflow.

### [REQ-MOB-003] Default-Collapsed Skill Pack Panels
- **Type**: Ubiquitous
- **Description**: When Agent Forge Studio renders the skill catalog, all skill pack tool item grids SHALL be collapsed by default (`hidden`) with chevrons rotated `-90deg`.
- **Acceptance Criteria**:
  1. Each `.pack-tools-grid` contains class `hidden` on initial load.
  2. Clicking the collapse button toggles between expanded and collapsed state.

### [REQ-MOB-004] Comprehensive Verification Gate
- **Type**: Ubiquitous
- **Description**: All automated test suites (Pytest, Vitest, Playwright smoke, ESLint, Ruff) SHALL pass with 100% green status.
- **Acceptance Criteria**:
  1. Playwright smoke tests pass without error.
  2. Vitest unit tests pass without error.
