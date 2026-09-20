---
id: CARD-390
title: "Standalone Skills Studio Runbook Editor and Mechanical Linter"
status: Ready
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:skills
  - area:web
  - area:cli
---

# [CARD-390] Standalone Skills Studio Runbook Editor and Mechanical Linter

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:skills`, `area:web`, `area:cli`  

---

## 1. Why / Intent (Beat 1)

In our architectural realignment, skills are Standard Operating Procedures (SOPs) written in natural language Markdown (`SKILL.md`) with YAML frontmatter. Unlike executable Python tools (which require sandbox test batteries and compiler gates), skills can be authored, updated, and refined fluidly.

Outside of Factory Studio, operators need a dedicated, interactive environment in **Skills Studio** (`#view-skills`) to:
1. Inspect all discovered platform and user skills across the system.
2. Author new `SKILL.md` runbooks from scratch or templates.
3. Edit existing runbooks with a live markdown editor.
4. Run the mechanical capability linter directly in the UI to guarantee ADR-0054 compliance (`len(requires_tools) <= 6`, description <= 60 chars, and verification contracts).

---

## 2. What AutoReiv Does Now (Beat 2)

1. Skills Studio (`src/web/static/modules/studios/skills.js`) provides a primarily read-only listing of skills.
2. Operators cannot author or edit `SKILL.md` runbooks directly inside Skills Studio; they are forced to write raw files by hand in `%LOCALAPPDATA%\AutoReiv\` or route through Factory Studio.
3. The mechanical capability linter (`src/application/skills/linter.py`) runs via the backend CLI (`autoreiv lint-skills`), but is not surfaced in the web UI for instant authoring feedback.

---

## 3. What Will Change (Beat 3)

1. **Two-Pane Skills Studio UI (`skills.js`, `index.html`)**:
   - **Left Pane (Skill Catalog)**: Searchable list of skills grouped by tier (Platform vs User Data), showing title, description, and declared tool count chips (`3 tools`).
   - **Right Pane (Runbook Workspace)**:
     - Header: Display Name, auto-slug, declared tools multiselect/chips, and `[ 🔍 Check Linter ]` / `[ 💾 Save Runbook ]` actions.
     - Live Markdown Editor with side-by-side preview toggle.
     - Interactive Linter Diagnostic Bar: Displays instant feedback (Tool count <= 6, description length, mandatory `## Verification` section).
2. **Backend Skill API Extensions**:
   - `POST /api/skills`: Create a new user skill under `$DATA_DIR/skills/<slug>/SKILL.md`.
   - `PUT /api/skills/{id}`: Update an existing user skill.
   - `POST /api/skills/lint`: Run `CapabilityLinter` against draft runbook content and return structured diagnostics without writing to disk.
3. **Template Scaffolding**:
   - Offer a "New Skill" template containing canonical sections: `## When to Use`, `## Required Tools`, `## Procedure`, `## Common Pitfalls`, `## Verification`.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire the static, read-only limitation of Skills Studio.
- Remove redundant or broken modal views that redirected skill authoring to dead endpoints.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-390-001] (Ubiquitous)**: THE SYSTEM SHALL allow browsing, viewing, creating, and editing `SKILL.md` runbooks directly in Skills Studio.
- **[REQ-390-002] (Event-Driven)**: WHEN an operator creates or edits a skill in Skills Studio, THE SYSTEM SHALL provide real-time or on-demand mechanical lint diagnostics via `POST /api/skills/lint`.
- **[REQ-390-003] (Event-Driven)**: WHEN an operator clicks `Save Runbook`, THE SYSTEM SHALL write the validated `SKILL.md` file to user data storage and refresh the active capability catalog.
- **[REQ-390-004] (State-Driven)**: WHILE authoring a skill, THE SYSTEM SHALL flag any skill declaring more than 6 tools as a warning/violation per ADR-0054 God-Agent threshold.
- **[REQ-390-005] (Negative Assertion)**: Automated tests shall explicitly assert that user skills are saved under `$DATA_DIR/skills/`, never inside the git checkout directory.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-390-skills-studio-editor` cut from `qa`.
- Backend tests: `tests/unit/skills/test_capability_linter.py`, `tests/unit/web/test_skills_api.py`.
- Frontend tests: Vitest for `skills.js` editor and linter status banner.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
