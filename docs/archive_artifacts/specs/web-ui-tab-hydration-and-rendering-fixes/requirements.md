# Requirements Specification: Web UI Tab Hydration And Rendering Fixes

> **Spec Status**: Approved  
> **Target Release**: Milestone 29  
> **Primary Component**: WebControlPlane

---

## 1. Executive Summary & Intent
Ensure all 7 tabs in AutoReiv's SPA control plane hydrate cleanly, render with full visual feedback, and provide accessible mobile/desktop controls with zero uncaught JavaScript errors.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-FIX-001]: Agent Studio Skill Pack Rendering
- **Type**: Event-Driven
- **EARS Statement**: `WHEN the operator navigates to Agent Studio, THE SYSTEM SHALL render all skill pack cards and tool checkboxes from the catalog regardless of previous caching state.`
- **Acceptance Criteria**:
  - [ ] Navigating to Agent Studio renders the 7 skill pack categories and 34 tools.
  - [ ] Selecting an agent checks its permitted tool checkboxes.

### [REQ-FIX-002]: System Info Topic Navigation & Viewer
- **Type**: Event-Driven
- **EARS Statement**: `WHEN the operator navigates to System Info, THE SYSTEM SHALL load and render the topic categories index and display the default architecture manual without throwing index errors.`
- **Acceptance Criteria**:
  - [ ] Topic categories render with active topic count.
  - [ ] Markdown documentation loads and renders with diagram support.

### [REQ-FIX-003]: Wiki Studio Vault Auto-Selection & Mobile Navigation
- **Type**: Event-Driven / Optional
- **EARS Statement**: `WHEN the operator navigates to Wiki Studio, THE SYSTEM SHALL render the folder tree and automatically load the first available note into the preview workspace.`
- **Acceptance Criteria**:
  - [ ] Vault tree renders inbox staging and warehouse notes.
  - [ ] First note is loaded into Markdown preview automatically.
  - [ ] On mobile viewports (<768px), drawer toggle button and visible action buttons are accessible.

### [REQ-FIX-004]: Wiki Mind Map & Graph Canvas Robustness
- **Type**: Event-Driven
- **EARS Statement**: `WHEN the operator clicks Mind Map or Graph view, THE SYSTEM SHALL render the physics canvas or knowledge graph modal without syntax or layout errors.`
- **Acceptance Criteria**:
  - [ ] Mind map opens with valid node count and physics simulation.
  - [ ] Knowledge graph opens and renders SVG diagram.

### [REQ-FIX-005]: Universal Tab Switching Error Quarantine
- **Type**: State-Driven
- **EARS Statement**: `WHILE switching tabs, THE SYSTEM SHALL isolate tab loaders with try/catch boundaries so that a failure in one tab does not break navigation or other tabs.`
- **Acceptance Criteria**:
  - [ ] Switching between any tabs executes smoothly without uncaught console errors.

---

## 3. Non-Functional & Boundary Constraints
- **Performance**: Tab switching and rendering in < 50ms.
- **Reliability**: Zero console exceptions on mobile or desktop viewports.
- **Compatibility**: Supports Chrome, Safari, Firefox on Desktop, iOS, Android.

---

## 4. Out of Scope
- Backend database schema migrations.

