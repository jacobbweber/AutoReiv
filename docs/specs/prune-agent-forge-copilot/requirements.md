# Requirements Specification: Prune Legacy System Architect CoPilot from Agent Forge Studio

## 1. System Intent & Scope
Clean up obsolete legacy "System Architect Co-Pilot" chat sidebar from Agent Forge Studio to eliminate obsolete system-agent calls, reduce DOM bloat, declutter the mobile/desktop layout, and expand the RPG Character Sheet cards to full workspace width.

---

## 2. EARS Requirements Matrix

### [REQ-PRUNE-001] Removal of Co-Pilot DOM Markup from Agent Forge Studio
- **Type**: Ubiquitous
- **Description**: The AutoReiv Web SPA SHALL not render the right-hand System Architect Co-Pilot column, Co-Pilot header, blueprint apply button, starter prompt chips, or prompt input form within `#view-agents`.
- **Acceptance Criteria**:
  1. The `#copilotMessages`, `#copilotForm`, `#copilotInput`, `#applyBlueprintBtn`, and `.copilot-chip` elements are removed from `src/web/templates/index.html`.
  2. The remaining Agent Forge character sheet cards occupy the main workspace container without column division artifacts.

### [REQ-PRUNE-002] Full-Width Responsive Agent Forge Character Sheet Layout
- **Type**: Ubiquitous
- **Description**: The Agent Forge character sheet container SHALL expand responsively across the full width of `#view-agents` on both mobile viewports and desktop resolutions.
- **Acceptance Criteria**:
  1. Character sheet cards (Identity, Persona, Constitution, Skill Scopes, Telemetry, Routines) are organized in a clean single-column or multi-column grid with `max-w-6xl mx-auto` or `w-full` padding.
  2. Scrolling is smooth and natural without vertical split-pane nesting bugs on mobile browsers.

### [REQ-PRUNE-003] Pruning of Co-Pilot Handlers and Event Listeners
- **Type**: Ubiquitous
- **Description**: The `src/web/static/modules/studios/forge.js` module SHALL not query Co-Pilot DOM elements or listen to Co-Pilot form submit events.
- **Acceptance Criteria**:
  1. Functions `appendCopilotMessage`, `extractAndOfferBlueprint`, and `checkForBlueprint` are removed from `forge.js`.
  2. Legacy streaming calls to `/api/chat/stream` with `agent_id: 'system-agent'` are completely removed from `forge.js`.
  3. No unhandled `null` reference errors occur during initialization of Agent Forge Studio.

### [REQ-PRUNE-004] Comprehensive Verification Gate
- **Type**: Ubiquitous
- **Description**: All automated test suites (Pytest, Vitest, ESLint, Playwright smoke) SHALL pass cleanly with zero errors.
- **Acceptance Criteria**:
  1. Playwright smoke tests pass without looking for obsolete Co-Pilot elements.
  2. Vitest and Pytest test suites maintain 100% green status.
