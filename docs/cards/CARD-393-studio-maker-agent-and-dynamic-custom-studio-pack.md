---
id: CARD-393
title: "Studio Maker Agent and Dynamic Custom Studio Pack"
status: Parked
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:studios
  - domain:agents
  - area:frontend
  - area:packs
---

# [CARD-393] Studio Maker Agent and Dynamic Custom Studio Pack

> **Status**: Parked  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:studios`, `domain:agents`, `area:frontend`, `area:packs`  

---

## 1. Why / Intent (Beat 1)

Operators need to create bespoke studios tailored to their workflows (e.g. SRE incident war-rooms, database inspectors, data pipeline monitors, custom agent control panels) directly inside AutoReiv without writing manual boilerplate HTML, CSS, and DOM wiring.

This card introduces the **Studio Maker** platform agent (`platform-packs/studio-maker`) and a **Declarative JSON Studio Engine**. Operators chat with Studio Maker to describe their workflow needs; the agent formulates, validates, and generates a structured declarative blueprint (`studio.json`), dynamically rendering the custom studio into AutoReiv's Desktop window manager and dock launcher with zero restart required.

---

## 2. What AutoReiv Does Now (Beat 2)

1. All studios (Chat, Agent Forge, Projects, Settings, Observe, Routines, Wiki, Factory, Prompts, Lumina) are statically hardcoded into `src/web/templates/index.html` and individual JavaScript modules.
2. Creating a new studio requires manual frontend software engineering: altering templates, editing the dock launcher, writing bespoke event handlers, and updating tab routers.
3. Operators cannot generate or customize studios dynamically through agent collaboration.

---

## 3. What Will Change (Beat 3)

1. **Declarative Studio Schema & Blueprint Engine (`studio.json`)**:
   - Define a structured JSON schema for declarative custom studios:
     - **Metadata**: `id`, `name`, `icon` (Lucide), `category`, `description`.
     - **Layout Grid**: Responsive panels (single-column, 2-column, 3-column, dashboard grid).
     - **Widget Components**: Metric cards, data tables, live log/event streams, Markdown readers, action buttons, form inputs, and interactive charts.
     - **Data Bindings**: REST endpoint bindings (`GET /api/*`) or tool executions to populate widgets.
     - **Action Triggers**: One-click buttons that trigger agent tasks, tool calls, or routines.
2. **Dynamic Studio Runtime Renderer (`src/web/static/modules/studios/dynamic_studio.js`)**:
   - Parses registered declarative studio manifests and injects them into the Radical Desktop stage.
   - Automatically registers dock icons and window management handles (drag, resize, minimize, maximize).
3. **Studio Maker Platform Agent Pack (`platform-packs/studio-maker/`)**:
   - Seeded platform agent with `studio-crafting` skill (`SKILL.md`).
   - Tools: `scaffold_custom_studio`, `validate_studio_manifest`, `preview_studio_layout`, `list_available_widgets`.
   - Conversational interview loop: interviews the operator on workflow goals, recommends layouts, generates valid `studio.json`, and installs it into user data (`studios/<id>/studio.json`).
4. **Studio Management API (`src/web/routers/studios.py`)**:
   - `GET /api/studios/custom`: Lists installed custom studios.
   - `POST /api/studios/custom`: Validates and saves custom studio blueprints.
   - `DELETE /api/studios/custom/{id}`: Uninstalls a custom studio.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire manual code edits to `index.html` for operator-level dashboard creation.
- Prune ad-hoc standalone dashboard HTML files in user data.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-393-001] (Ubiquitous)**: THE SYSTEM SHALL support declarative custom studios defined by a validated `studio.json` manifest stored in user data.
- **[REQ-393-002] (Event-Driven)**: WHEN an operator collaborates with Studio Maker in Chat Studio, THE AGENT SHALL validate draft layouts against the Studio JSON Schema and persist the generated studio blueprint.
- **[REQ-393-003] (State-Driven)**: WHILE a custom studio is registered, THE DYNAMIC STUDIO RENDERER SHALL paint the studio window, register its dock launcher icon, and bind its configured data sources and action buttons.
- **[REQ-393-004] (Negative Assertion)**: Automated tests shall explicitly assert that malformed studio manifests (missing required metadata, invalid widget types, or syntax errors) are rejected with clear validation diagnostics and never crash the desktop stage.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-393-studio-maker-agent` cut from `qa`.
- Unit tests: `tests/unit/studios/test_studio_manifest_schema.py`, `tests/unit/frontend/dynamic_studio_renderer.test.js`.
- Integration test: `tests/integration/studios/test_studio_maker_lifecycle.py`.
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/preflight/scripts/preflight.py`.
