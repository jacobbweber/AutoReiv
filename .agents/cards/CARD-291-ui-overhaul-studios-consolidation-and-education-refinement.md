# [CARD-291] UI Overhaul: Studio Consolidation, High-Signal Design System & Education Studio Refinement

> **Status**: Done  
> **Created**: 2026-09-13
> **Spec Reference**: Priority 1 UI Overhaul (Jacob /goal 2026-09-13). Multi-studio design system unification, clutter elimination, duplicate lever consolidation, and dramatic Education Studio pedagogy UX elevation.
> **Labels**: `type:feature`, `ui`, `design-system`, `studios`, `education`, `priority-1`
> **Branch**: `feat/grok-ui-overhaul` off `qa`
> **Baseline Snapshot**: `grok-qa-baseline` (frozen untouched backup)

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Developer B2B Technical Minimal Aesthetic**: Transform the OS desktop multi-window environment into a unified, high-contrast, low-noise control plane (pitch void backgrounds `#08090C`/`#0E1015`, hairline borders `rgba(255,255,255,0.08)`, monospace counters/timestamps, and crisp sans-serif headers).
2. **Mathematical Border-Radius Harmony**: Strictly enforce concentric radii across all studios: `outer_radius = inner_radius + padding`. Small controls (badges, tags) get 4px (`rounded-sm`), medium controls (buttons, inputs) get 8px (`rounded-md`), cards get 12px (`rounded-xl`), modals/sheets get 16px (`rounded-2xl`). Snapped window edges drop border radius to 0 (`rounded-none`).
3. **Strict Signal Hierarchy**: Eliminate visual noise. Never stack an ambient status dot (emerald/amber/rose) and a numeric count badge on the same line item. Numeric counts are reserved strictly for pending operator actions. Ambient status indicates presence/health.
4. **De-duplicate Levers & Remove Misplaced Elements**:
   - Settings Studio is the canonical source of truth for LLM providers, credentials, and hardware fit. Agent Studio must not duplicate the entire API endpoint and model discovery form.
   - Agent creation and training triggers are unified so Chat, Agent Studio, and Factory Studio each have a clear, non-redundant role.
5. **Drastic Elevation of Education Studio**:
   - Strip out raw internal developer labels ("CARD-242", "CARD-245", "binary external verify (not LLM self-score)", "edutainment refused") and unstyled multi-color button clusters.
   - Re-architect into an inspiring, high-signal **Interactive Learning Cockpit**:
     - Top Learner Telemetry HUD (mastered concepts, due reviews count, retention streak).
     - Single unified Smart Review Action ("Next Quiz / Due Review") replacing 4 redundant buttons.
     - Four clean, focused modes: **Study & Flashcards**, **Explain-it-Back (Elaboration)**, **Application Lab (Exercises)**, and **Mastery & Error Analysis**.
     - Embedded visual concept flow / Mermaid diagram renderer that enhances retrieval without clutter.

### Beat 2: What AutoReiv Does Now
1. **Agent Studio (`view-agents`)** is an 8-card scrolling mountain:
   - Duplicates the full LLM Provider form (`#forgeProviderSelect`, API Base URL, API Key, `[Refresh Models]` button) already present in Settings Studio.
   - Surrounds the operator with redundant creation buttons (`New Agent`, `Quick Scaffold`, `Import`) and an autonomous self-scaffold candidate table.
2. **Chat Studio (`view-chat`)**:
   - Top bar contains 6 loosely organized buttons without clear signal grouping.
   - Options drawer mixes prompt quick-picks, token compaction, reflexion verification, and autonomous lab loops.
   - Tool execution runs appear as plain text boxes rather than structured step traces.
3. **Education Studio (`view-education`)**:
   - Currently a developer scaffold displaying 7 stacked raw panels with hardcoded "CARD-xxx" badges.
   - Has 4 separate buttons for "Next quiz" (`Next quiz (weak/due)`, `Next quiz (miss-reason pressure)`, `Next quiz (delivery)`, `Next quiz (amplified)`).
   - Shows raw item IDs (`edu_...`) and debugging notes instead of a sleek, motivating study interface.
4. **Visual Inconsistency Across Windows**:
   - Mismatched border radii, inconsistent button colors (mixture of indigo, brand, emerald, sky, amber, fuchsia, teal, rose without strict semantic meaning), and wide table rows that overflow on smaller viewports.

### Beat 3: What Will Change
1. **Phase 1: Foundation & Agent Desktop Window Shell**:
   - Enforce global design tokens in `index.html` and `agent-desktop.js`: pitch-void surfaces, hairline border strokes, concentric radii utility classes, and radial edge glow on active focused windows.
   - Bottom Dock: Clean taskbar with crisp status indicators, action count badges, and zero-radius edge snapping.
2. **Phase 2: Agent Studio Consolidation (`view-agents`)**:
   - De-duplicate LLM Provider: Replace the heavy endpoint form with a sleek single-line override card that references Settings Studio.
   - Streamline the 8-card sheet into 4 logical zones: Identity & Persona, Operating Constitution, Skills & Tools (Platform vs Pack), and Dedicated Integrations (MCP/Storage/Brain).
3. **Phase 3: Education Studio Total Transformation (`view-education`)**:
   - Transform from 7 developer panels into a polished 4-tab Learning Cockpit:
     - Tab 1: **Study & Retrieval (Quiz)** with clean flashcards, answer input, and embedded Mermaid visual amplifiers.
     - Tab 2: **Feynman Explain-it-Back (Elaboration)** with comprehension prompts and instant feedback.
     - Tab 3: **Application Lab** with coding/exercise challenges and one-click Exercise Job minting.
     - Tab 4: **Mastery & Metacognition** with error logs, weak concept tracking, and retention schedule.
   - Unify all "Next quiz" triggers into a single adaptive "Start Review" button.
   - Purge all raw "CARD-xxx" and engineering jargon from the user-facing UI.
4. **Phase 4: Chat Studio HUD & ReAct Trace Streamlining (`view-chat`)**:
   - Top bar: Streamlined telemetry strip (Agent avatar, name, tone, online status, and grouped action icons).
   - Tool execution cards: Alternating or vertical trace spine (`01 LOOK -> 02 DO -> 03 SEE`) with monospace step counters and latency badges.
   - Input HUD: Clean floating composer with progressive disclosure options drawer.
5. **Phase 5: Cross-Studio Polish (Settings, Factory, Wiki, Observability, Routines, Projects, Prompts)**:
   - Settings Studio: Solidify as single source of truth for providers and credentials; clean two-line responsive rows.
   - Factory Studio: Polish 8-phase pipeline flowchart with crisp mono badges and consolidated training backlog.
   - Wiki Studio: 2-line notes tree, telemetry strip under note titles, clean frontmatter inspector.
   - Observability, Routines, Projects, Prompts: Apply concentric radii, dark void styling, and one-signal-per-row standard.
6. **Phase 6: Verification & Quality Gate**:
   - Zero lint errors (`npm run lint:frontend`).
   - 100% green unit and e2e tests (`npm run test:unit:frontend`).
   - Live browser smoke verification across all 10 studios.

---

## 2. Acceptance Criteria

- [x] **[REQ-UI-291-001] Concentric Radii & Void Theme**: All window frames, cards, buttons, and badges obey `inner = outer - padding` and dark void palette (`#08090C` / `#0E1015`).
- [x] **[REQ-UI-291-002] Agent Studio Consolidation**: Remove duplicate LLM provider configuration forms from Agent Studio; condense into a single-line override referencing Settings Studio.
- [x] **[REQ-UI-291-003] Education Studio Cockpit**: Rebuild `view-education` into a 4-tab Interactive Learning Cockpit (Study/Quiz, Elaboration, Application, Mastery); remove all "CARD-xxx" jargon; unify the 4 redundant "Next quiz" buttons into a single smart adaptive action.
- [x] **[REQ-UI-291-004] Chat Studio Trace & HUD**: Format agent tool calls with vertical ReAct trace spine styling and clean status badges; streamline top bar actions.
- [x] **[REQ-UI-291-005] Signal-to-Noise Purity**: Never stack an ambient status dot and an actionable count badge on the same line item across any studio.
- [x] **[REQ-UI-291-006] Quality Gates Green**: Vitest unit tests pass 100%, ESLint passes with 0 errors, and all studio features remain 100% functional.

---

## 3. Constraints

- Never break existing backend APIs or state schemas (`store.js`, `api.js`).
- Preserve all existing capabilities: tests must pass without regressions.
- No third-party product names in UI or cards.
- Work on branch `feat/grok-ui-overhaul`; keep `grok-qa-baseline` untouched.
