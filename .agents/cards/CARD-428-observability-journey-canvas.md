---
id: CARD-428
title: "Observability Journey Canvas"
status: Done
created: 2026-09-23
adr: none
labels:
  - type:feature
  - observability
  - ui-ux
---

# [CARD-428] Observability Journey Canvas

> **Status**: Done  
> **Created**: 2026-09-23  
> **ADR Reference**: [ADR-0055](../adr/0055-operator-contract-testing-and-suite-hygiene.md)  
> **Labels**: `type:feature`, `observability`, `ui-ux`

---

## 1. Why / Intent (Beat 1)

Allow operators to visually trace end-to-end user operations across UI, API, Orchestrator, and Storage with interactive Code and Payload inspection. This directly cures the mental opacity of agentic codebases by presenting dynamic execution journeys across architectural swimlanes with synchronized code snippets and runtime state transitions.

---

## 2. What AutoReiv Does Now (Beat 2)

Observability Studio (`observability.js`) displays static KPI cards (turns, tokens, cost, latency), an agent KPI table, a tool reliability table, system logs terminal, and a basic text-only `standingJourneyTimeline` (`[CARD-227]`).
The current timeline only outputs flat log lines for background batch jobs without:
- Visual architectural swimlanes (UI, API Gateway, Orchestrator State Machine, Storage & Policy).
- Chronological node layout with directed connecting flow vectors.
- Interactive step-by-step playback scrubber (Step forward, Step back, Autoplay).
- Synchronized Code Inspector displaying exact source code lines for any selected step.
- Runtime State Transition badge and formatted Payload Inspector.

---

## 3. What Will Change (Beat 3)

1. **Backend Application Service & Models (`src/application/observability/journey_canvas.py`)**:
   - `JourneyCanvasService`: Manages canonical and live journey traces.
   - Built-in canonical scenarios representing real architectural paths:
     - `chat_turn_hitl_approval`: Chat Submit $\rightarrow$ FastAPI Router $\rightarrow$ ReAct Loop $\rightarrow$ Tool Policy Gate (HITL pause) $\rightarrow$ Resume $\rightarrow$ Streamed response.
     - `routine_wiki_execution`: Scheduled Cron Wakeup $\rightarrow$ Orchestrator $\rightarrow$ Research Skill $\rightarrow$ Wiki Note Create $\rightarrow$ Storage.
     - `react_multi_turn_reasoning`: User Query $\rightarrow$ Agent Plan $\rightarrow$ Search Tool $\rightarrow$ Observation $\rightarrow$ Synthesize $\rightarrow$ Complete.
   - Domain models: `JourneyScenario`, `JourneyStep`, `SourceSnippetResponse`, `SwimlaneDefinition`.
2. **FastAPI Endpoints (`src/web/routers/observability.py`)**:
   - `GET /api/observability/journey-canvas/scenarios`: Returns catalog of scenarios.
   - `GET /api/observability/journey-canvas/scenarios/{scenario_id}`: Returns complete journey steps, metadata, and state transitions.
   - `GET /api/observability/journey-canvas/source`: Safely retrieves repository source lines around a target line with path-traversal boundary enforcement.
3. **Frontend Submodule (`src/web/static/modules/observability/journey_canvas.js`)**:
   - Modular submodule (strictly under 800 lines).
   - Renders 4 horizontal swimlanes:
     1. `1. UI / Browser`
     2. `2. API Gateway (FastAPI)`
     3. `3. Orchestrator State Machine (ReAct Loop)`
     4. `4. Storage & Policy`
   - Interactive SVG connectors linking sequential nodes across swimlanes.
   - Timeline controls: Step Back, Play/Pause toggle, Step Forward, and interactive scrubber slider.
   - Selected step drawer:
     - Code Inspector: formatted code snippet, line numbers, highlighted active line, IDE deep link.
     - Runtime State Badge: transition pill (e.g. `PLANNING -> AWAITING_APPROVAL`).
     - Payload Inspector: syntax-highlighted JSON viewer with a copy button.
4. **HTML Template Integration (`src/web/templates/index.html`)**:
   - Dedicated `<details class="obs-section" data-obs-section="journey-canvas" open>` section inside Observability Studio.
5. **Observability Orchestrator Integration (`src/web/static/modules/studios/observability.js`)**:
   - Cleanly imports and initializes `initJourneyCanvas()`.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **Retire**: Ad-hoc manual code-grepping when diagnosing agent execution flow.
- **Supersede**: Flat text-only job logs as the sole way to observe multi-step operations.
- **Strict Boundary**: No shadow APIs or duplicate fetchers; all source and journey queries use the canonical `/api/observability/journey-canvas/*` endpoints.

---

## 5. Acceptance Criteria (EARS Syntax)

- **Ubiquitous**: THE SYSTEM SHALL render a dedicated Journey Canvas section within Observability Studio containing four architectural swimlanes: UI / Browser, API Gateway (FastAPI), Orchestrator State Machine (ReAct Loop), and Storage & Policy.
- **Ubiquitous**: THE SYSTEM SHALL render a synchronized Code Inspector and Payload Inspector beside or beneath the journey canvas.
- **Event-Driven**: WHEN an operator selects a scenario from the scenario selector, THE SYSTEM SHALL fetch `/api/observability/journey-canvas/scenarios/{scenario_id}` and render the step cards with SVG flow paths.
- **Event-Driven**: WHEN an operator clicks any step card or adjusts the playback slider, THE SYSTEM SHALL activate that step, highlight its node with an active glow border, and load the corresponding source snippet via `/api/observability/journey-canvas/source`.
- **Event-Driven**: WHEN an operator toggles the Play button, THE SYSTEM SHALL automatically advance the active step at a timed interval until paused or reaching the final step.
- **Negative Assertion**: Automated tests shall explicitly assert that `/api/observability/journey-canvas/source` refuses file paths outside the repository checkout root with HTTP 403 or 400 (anti-path-traversal invariant).
- **Negative Assertion**: Automated tests shall explicitly assert that requesting an unknown scenario ID returns HTTP 404 with an error payload rather than an empty 200 success.
- **Negative Assertion**: Automated tests shall assert that every step in a returned scenario contains valid `swimlane`, `source_file`, `source_line`, and `state_transition` fields.

---

## 6. Constraints & Verification Plan

- Backend unit & operator contract tests under `tests/unit/observability/test_journey_canvas.py`.
- Frontend unit tests under `tests/unit/frontend/journey_canvas.test.js`.
- Security path-traversal tests under `tests/unit/observability/test_journey_canvas_security.py`.
- Monolith hygiene: `journey_canvas.js` strictly under 800 lines.
- Static linter: `ruff check .` with 0 errors; `npm run lint:frontend` with 0 errors.
- Preflight verification passes.
