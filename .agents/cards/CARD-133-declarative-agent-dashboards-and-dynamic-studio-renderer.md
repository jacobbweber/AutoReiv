# [CARD-133] Declarative Agent Dashboards (dashboard.json) and Dynamic Studio Renderer

> **Status**: Done
> **Created**: 2026-08-31
> **Spec Reference**: CARD-003; CARD-104; CARD-124; CARD-127
> **Labels**: `type:feat`, `type:ui`, `type:agents`, `type:plugins`

---

## 1. Why / Intent
Users want agent packs to be capable of contributing their own dedicated visual Studio pages (e.g. Garden Studio, Home Lab Studio, 3D Printer Studio) without needing to code custom HTML/JS. By introducing an optional, declarative `dashboard.json` schema and a generic Dynamic Studio Renderer in AutoReiv's frontend, any agent pack can declare interactive metric cards, data tables, action buttons, and live Markdown editors that render natively in the UI and connect directly to agent tools.

---

## 2. Visual Contract & ASCII Wireframes

### Dynamic Studio Tab in AutoReiv Navigation
```text
+--------------------------------------------------------------------------+
| [💬 Chat] [🛠️ Agent Studio] [📁 Projects] [📖 Wiki] [🌿 Garden Studio]      |
+--------------------------------------------------------------------------+
```

### Rendered Dynamic Dashboard Viewport (`#dynamicStudio`)
```text
+--------------------------------------------------------------------------+
| 🌿 Garden Studio (Gardening Agent)                    [ 🔄 Refresh Data ]|
+--------------------------------------------------------------------------+
| [ 💧 Soil Moisture: 68% (Optimal) ]        [ 🍅 Days to Harvest: 14 ]    |
|                                                                          |
| QUICK ACTIONS                                                            |
| [ 💧 Water Bed 1 ]   [ 🌿 Spray Nutrients ]   [ 🔄 Scan Sensor Mesh ]    |
| ------------------------------------------------------------------------ |
|                                                                          |
| ACTIVE PLANT ROSTER                                                      |
| ------------------------------------------------------------------------ |
| Plant Name       | Bed / Location | Status       | Actions               |
| Roma Tomatoes    | Bed 1          | Healthy 🟢   | [ 💧 Water ] [ Log ]  |
| Sweet Basil      | Pot A          | Dry ⚠️       | [ 💧 Water ] [ Log ]  |
| ------------------------------------------------------------------------ |
|                                                                          |
| 📝 DAILY GARDEN JOURNAL                                     [ 💾 Save ]  |
| ------------------------------------------------------------------------ |
| # Summer Garden Notes                                                    |
| - [x] Morning irrigation completed for Bed 1                             |
| - [x] Check basil soil moisture in afternoon                             |
|                                                                          |
| Observations: Roma tomatoes flowering nicely.                            |
+--------------------------------------------------------------------------+
```

---

## 3. What to Build

### Slice 1: Declarative Dashboard Schema & Models
- In `src/application/agent_packs/schema.py`:
  - Define `DashboardCardType` enum (`stat_group`, `action_group`, `data_table`, `markdown_editor`, `markdown_viewer`).
  - Define `DashboardCardDefinition` (type, title, width, icon, accent, source_tool, action_tools, file_path, save_tool, etc.).
  - Define `AgentDashboardManifest` (`tab_title: str`, `icon: str`, `cards: List[DashboardCardDefinition]`).
  - Add optional `dashboard: Optional[AgentDashboardManifest] = None` to `AgentPackManifest` (or loaded from `dashboard.json`).

### Slice 2: AutoReiv Agent Platform Tools
- In `src/application/skills/agent_builder_tools.py` (and AutoReiv agent platform tools):
  - Add `scaffold_agent_dashboard(pack_id, tab_title, icon, cards_json)`: generates and validates `dashboard.json` for an agent pack.
  - Add `read_agent_dashboard(pack_id)`: returns parsed dashboard manifest.

### Slice 3: Backend REST Endpoints
- In `src/web/routers/agent_packs.py` / `src/web/routers/studios.py`:
  - `GET /api/agent-packs/dashboards`: Returns all active dynamic studio manifests from installed packs.
  - `POST /api/agent-packs/{pack_id}/dashboard`: Saves or updates `dashboard.json`.
  - `POST /api/agent-packs/action`: Executes a declared dashboard action tool and returns updated state.

### Slice 4: Frontend Dynamic Studio Renderer
- In `src/web/templates/index.html`:
  - Add `#dynamicStudio` container with header, card grid, action toolbar, and markdown editor slot.
- In `src/web/static/modules/studios/dynamic_studio.js` (NEW):
  - Dynamically mounts nav items to `#sidebarNav` and mobile selector when packs with dashboards are loaded.
  - Reads card manifests and renders Tailwind-styled Stat Cards, Action Buttons, Tables, and live Markdown Editor (powered by existing markdown engine).
  - Wires action buttons to trigger tool calls and display toast feedback.

### Slice 5: Gardening Pack Seed & Verification
- Create sample `agent-packs/gardening/` (or seed in data directory) containing `pack.json`, `SKILL.md`, and `dashboard.json` with soil moisture sensors, watering action buttons, and daily garden journal editor.

---

## 4. EARS Requirements & Acceptance Criteria

- `[REQ-DASH-001]` **Declarative Dashboard Schema**: When an agent pack includes `dashboard.json`, the pack loader shall validate the schema against `AgentDashboardManifest`.
- `[REQ-DASH-002]` **Dynamic Studio Discovery**: When the web client loads `/api/agent-packs/dashboards`, the backend shall return all valid dashboard configurations from installed packs.
- `[REQ-DASH-003]` **Dynamic Nav Registration**: When a pack with a dashboard is installed, the frontend navigation bar shall automatically display the pack's custom studio tab with its configured icon and title.
- `[REQ-DASH-004]` **Interactive Card Components**: When viewing a dynamic studio, the renderer shall support Stat Groups, Action Buttons (which execute tools with loading state), Data Tables, and live Markdown Viewers/Editors.
- `[REQ-DASH-005]` **AutoReiv Dashboard Authoring Tools**: The `AutoReiv` agent platform pack shall have tools to scaffold and edit `dashboard.json` for any agent pack.
- `[REQ-DASH-006]` **Clean Lifecycle**: When a pack with a dashboard is uninstalled or deleted, its dynamic studio tab shall be removed from the UI immediately.
- [x] All automated unit & integration tests pass cleanly via `pytest`.
- [x] Frontend vitest tests pass cleanly.
- [x] Zero lint errors via `ruff check .`.
- [x] Local commit on `qa`. Card status `In Review` after code.

---

## 5. Constraints
- Work on `qa`. Do not push or tag unless explicitly asked.
- Must remain 100% optional: packs without `dashboard.json` continue working purely in Chat Studio.
- Reuse AutoReiv's existing markdown parser (`marked.js`) and Tailwind dark-slate design system.
- Card stays Ready until Jacob approves build.
