# [CARD-194] Flows Studio Visual Canvas and Execution Graph Engine

> **Status**: Backlog
> **Created**: 2026-09-08
> **Spec Reference**: `docs/adr/0014-execution-primitives-taxonomy.md`; CARD-174
> **Labels**: `type:epic`, `AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Flows`

---

## 1. Three Beats

### Beat 1: What you mean
AutoReiv currently has dedicated studios for configuring agents (Agent Studio), running time-based background tasks (Routines Studio), and developing codebases (Projects Studio). 

However, operators need to orchestrate complex, multi-stage, multi-agent processes and automated pipelines—such as customer support routing, document processing pipelines, multi-analyst research loops, and self-healing operations.

You want a dedicated **Flows Studio** featuring:
1. An intuitive, drag-and-drop **Visual Authoring Canvas** where you can place nodes (Agents, LLM Prompts, Platform Tools, Code Runners, Conditional Branching, and Human-in-the-Loop gates) and wire them together with directed edges.
2. An underlying **Graph State Machine Engine** that executes the flow with state isolation, parallel fan-out, conditional branch routing, and pause/resume checkpoints.
3. A real-time **Flow Run Visualizer** that highlights nodes live as they run (pulsing blue for active, green for success, red for error, amber for waiting approval) with clickable node inspectors showing inputs, outputs, and logs.

This primitive is kept completely distinct from the Agent Training Factory (which remains a dedicated, industrial agent manufacturing plant).

### Beat 2: What AutoReiv does now
1. **Existing Execution Primitives**:
   - `AgentKernel`: Turn-level ReAct execution for conversational chat.
   - `PlanAndExecuteEngine`: Sequential 2-to-6 phase goal breakdown for a single agent.
   - `RoutineScheduler`: Clock-based background runner for periodic routines.
   - `FactoryOrchestrator`: Hardcoded 8-stage cyclical state machine purpose-built exclusively for training and certifying agent packs.
2. **Missing Flow Authoring**:
   - There is no visual canvas or user-definable graph engine.
   - Users cannot create, save, or run custom multi-node, multi-agent pipelines.
   - There is no generic Flow Run Visualizer.

### Beat 3: What will change
1. **Flows Studio UI (`src/web/templates/index.html`, `src/web/static/modules/studios/flows.js`)**:
   - Add "Flows" to the primary left navigation bar alongside Agents, Projects, Wiki, and Routines.
   - **Canvas Workspace**: Node-based canvas supporting drag-and-drop node creation, connection snapping, zooming, panning, and auto-layout.
   - **Node Palette**:
     - *Agent Node*: Invokes a specific Platform or User Agent with an input prompt and memory context.
     - *Prompt / LLM Node*: Direct LLM inference with customizable system prompts and model selection.
     - *Tool Node*: Direct execution of any registered platform or agent tool.
     - *Code Node*: Sandboxed Python or PowerShell script execution.
     - *Condition / Router Node*: Evaluates rules or LLM classifications to route execution down branch A or branch B.
     - *HITL Gate Node*: Pauses execution until a human operator reviews and approves intermediate outputs.
2. **Execution Graph Engine (`src/application/flows/`)**:
   - Directed acyclic and cyclic graph engine (DAG) with topological sorting and cycle detection.
   - Shared flow state context dictionary flowing from output pins to input pins.
   - Durable pause/resume and state checkpointing in SQLite.
3. **Flow Run Visualizer**:
   - Live execution viewer showing the path taken by the flow in real time.
   - Clicking any completed or running node opens a sidebar inspector displaying exact input payload, output data, execution latency, and token telemetry.
4. **Persistence & REST API**:
   - SQLite tables: `flows`, `flow_nodes`, `flow_edges`, `flow_runs`, `flow_step_logs`.
   - REST endpoints: `GET/POST /api/flows`, `GET/PUT/DELETE /api/flows/{flow_id}`, `POST /api/flows/{flow_id}/run`, `GET /api/flows/runs/{run_id}`.

---

## 2. Acceptance Criteria (Definition of Done)

- [ ] **AC-1**: Flows Studio navigation item and dual-pane layout (Flow catalog + Visual Canvas) added to the web UI.
- [ ] **AC-2**: Visual canvas supports creating, moving, and connecting nodes (Agent, LLM Prompt, Tool, Condition, HITL Gate).
- [ ] **AC-3**: Graph engine executes multi-node flows with state passing and branch routing.
- [ ] **AC-4**: Flow Run Visualizer provides real-time node state illumination (running, passed, failed, paused).
- [ ] **AC-5**: Clicking nodes during or after execution inspects input, output, and token telemetry.
- [ ] **AC-6**: Flow definitions and historical run records persist in SQLite.
- [ ] **AC-7**: Unit and integration tests verify graph topology, execution routing, and API endpoints.
- [ ] **AC-8**: Zero lint errors via `ruff check .` and frontend tests pass cleanly.

---

## 3. Constraints & Architecture Invariants

- Kept strictly decoupled from the Agent Training Factory; ATF retains its specialized sandbox verification machinery.
- Follows the DotAgents Protocol and AutoReiv SQLite repository pattern.
- Backlog card only; implementation begins when scheduled and approved by the visionary.
