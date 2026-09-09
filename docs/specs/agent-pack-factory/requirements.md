# Requirements Specification: Autonomous Agent Pack Factory and Self-Testing Capability Loop

> **Spec Status**: Approved Specification  
> **Version**: 1.0.0  
> **Target Release**: v0.20.0  
> **Primary Component**: AutoReiv.Orchestration / AutoReiv.Kernel / AutoReiv.Skills / AutoReiv.Agents  
> **Card Reference**: [CARD-159](file:///.github/cards/CARD-159-autonomous-agent-pack-factory-and-self-testing-capability-loop.md)  
> **ADR Reference**: [docs/adr/0048-autonomous-agent-pack-factory-and-capability-loop.md](file:///D:/Projects/Active/AutoReiv/docs/adr/0048-autonomous-agent-pack-factory-and-capability-loop.md)  

---

## 1. Executive Summary & Intent

Users want AutoReiv to autonomously create, train, test, and optimize new specialist agents (e.g., Linux Game Server Host, Personal Finance, HomeLab Sysadmin) without requiring manual Python coding, schema design, or prompt engineering.

Users with substantial local compute (e.g., 128GB unified memory running local Ollama 32B/72B models) have free, continuous capacity for overnight execution. Rather than inventing brittle tools on the fly during live chat turns, AutoReiv executes an **autonomous overnight capability loop (The Factory in a Lab)**:
1. Discovers target environment details (read-only).
2. Authors focused, atomic Python tools and runbooks.
3. Tests tools in an isolated sandbox against simulated mocks.
4. Consolidates tool bloat and enforces split policies to protect local model context windows.
5. Verifies correctness through an exhaustive 4-stage automated testing battery.

### Core Architectural Invariant: Factory vs. User Packs
- **Factory Machinery (Platform Packs in `platform-packs/`)**: Built-in specialist roles (`conductor`, `inspector`, `coder`, `sandbox_runner`, `critic`) configured with `show_in_chat: false` so they do not clutter chat menus.
- **Factory Output (User Agent Packs in `$DATA_DIR/packs/<agent_id>/`)**: All authored tools, runbooks, and definitions are written strictly inside self-contained, portable User Agent Packs.
- **Pack Scoping & Local Model Economy**: Tools belong to the specific agent pack being trained. Local models never see massive global tool registries; they receive only the 3–6 tools strictly relevant to their role.

---

## 2. Requirements Matrix (EARS Notation)

### [REQ-FACT-001]: Isolated User Pack Authoring Invariant
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL author, modify, and store all generated agent tools, skills, and configuration files strictly inside the target User Agent Pack directory (`$DATA_DIR/packs/<agent_id>/`).
- **Acceptance Criteria**:
  - [ ] No factory-generated tools or runbooks are written to `platform-packs/` or global platform directories.
  - [ ] Generated tool Python files are saved under `$DATA_DIR/packs/<agent_id>/tools/<tool_name>.py`.
  - [ ] Generated skill runbooks are saved under `$DATA_DIR/packs/<agent_id>/skills/<skill_name>/SKILL.md`.
  - [ ] The pack manifest `$DATA_DIR/packs/<agent_id>/pack.json` references only tools and skills contained within that pack.
  - [ ] Exporting the pack via `export_agent_pack` yields a fully self-contained `.zip` package.

### [REQ-FACT-002]: Core Platform Factory Pack Roster
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL provide five dedicated Core Platform Factory Agent Packs under `platform-packs/` with `show_in_chat: false` by default: Conductor, Inspector, Coder, Sandbox Runner, and SRE Critic.
- **Acceptance Criteria**:
  - [ ] **Conductor** (`platform-packs/conductor/`): Orchestrates the training graph, tracks seed objectives, routes work, and commits verified tools. Toolset scoped to delegation and pack registration.
  - [ ] **Inspector** (`platform-packs/inspector/`): Executes read-only discovery probes on target environments and compiles structured `EnvironmentManifest` data. Toolset scoped to read-only inspection.
  - [ ] **Coder** (`platform-packs/coder/`): Authors Python tools and `SKILL.md` runbooks inside the target pack. Toolset scoped to code authoring and file editing.
  - [ ] **Sandbox Runner** (`platform-packs/sandbox_runner/`): Configures mock environments and executes tools in the local sandbox (`EphemeralSandbox`). Toolset scoped to sandbox execution.
  - [ ] **SRE Critic** (`platform-packs/critic/`): Audits code quality, regex safety, error handling, and security invariants. Toolset scoped to read-only inspection.
  - [ ] All five agents are excluded from Chat Studio picker dropdowns by default (`show_in_chat: false`).

### [REQ-FACT-003]: Typed SQLite Packet Interchange
- **Type**: Event-Driven
- **EARS Statement**: WHEN factory agents transition between graph nodes, THE SYSTEM SHALL communicate exclusively via typed SQLite packets rather than unstructured chat history transcripts.
- **Acceptance Criteria**:
  - [ ] **WorkPacket**: Contains `goal`, `facts`, `constraints`, `done_when`, and `budget`.
  - [ ] **GapPacket**: Contains `kind` (`tool` | `skill` | `agent` | `graph_edge`), `justification`, `evidence`, and `suggested_signature`.
  - [ ] **EvalPacket**: Contains `checks_executed`, `passed`, `stdout`, `stderr`, and `duration_ms`.
  - [ ] **PromotePacket**: Contains `modified_files`, `test_scores`, `critic_verdict`, and `hitl_approval_id`.
  - [ ] Packets are stored in the SQLite `factory_packets` table and linked by `job_id` and `node_id`.

### [REQ-FACT-004]: Conditional Graph Orchestrator
- **Type**: State-Driven
- **EARS Statement**: WHILE executing an agent training job, THE SYSTEM SHALL advance execution using a deterministic Graph Walker following conditional edges (`ok`, `fail`, `need_capability`, `need_human`).
- **Acceptance Criteria**:
  - [ ] Graph nodes support types: `attempt` (worker execution), `conduct` (conductor routing), `eval` (sandbox test execution), `critic` (SRE review), `hitl` (human approval gate).
  - [ ] Transitions are evaluated without language model inference inside the orchestrator loop.
  - [ ] If a worker emits `need_capability`, the engine routes to the `conduct` node.
  - [ ] If an evaluation fails, the engine routes back to `conduct` with the structured `EvalPacket`.
  - [ ] Graph definitions are versioned and stored in SQLite `factory_graphs`.

### [REQ-FACT-005]: Socratic Handshake UX
- **Type**: User-Initiated
- **EARS Statement**: WHEN a user requests a new agent with "Train Agent" enabled, THE SYSTEM SHALL present a concise 3-question Socratic handshake in Chat Studio to capture seed objectives without requiring technical specifications.
- **Acceptance Criteria**:
  - [ ] Question 1 (Target): Captures whether the target is local or remote (e.g., path or SSH host).
  - [ ] Question 2 (Objectives): Presents 3 recommended primary actions based on the user's intent.
  - [ ] Question 3 (Risk): Captures confirmation preference for destructive or mutating operations.
  - [ ] Total interaction time for the user is under 45 seconds.
  - [ ] Responses are converted into initial `WorkPacket` seed goals.

### [REQ-FACT-006]: Autonomous Environment Discovery Probe
- **Type**: Event-Driven
- **EARS Statement**: WHEN a training job initializes, THE SYSTEM SHALL execute a safe, read-only discovery probe against the target host or directory to extract ground truth environment details.
- **Acceptance Criteria**:
  - [ ] Discovers operating system, shell environment, and permissions.
  - [ ] Discovers file paths, binary locations, and directory structures.
  - [ ] Discovers configuration file formats (`.ini`, `.yaml`, `.json`, `.env`, `.toml`).
  - [ ] Discovers process runtime managers (`systemd`, `docker-compose`, standalone daemon, cron).
  - [ ] Compiles an immutable `EnvironmentManifest` stored in the job context.
  - [ ] Zero mutating or destructive commands are permitted during this phase.

### [REQ-FACT-007]: Domain SOP & Best-Practice Ingestion
- **Type**: State-Driven
- **EARS Statement**: WHILE designing tool blueprints, THE SYSTEM SHALL cross-reference domain documentation and operational constraints for the discovered target software.
- **Acceptance Criteria**:
  - [ ] Extracts operational constraints (e.g., "service must be stopped before modifying configuration").
  - [ ] Extracts backup preservation invariants (e.g., "always retain at least 3 historical save archives").
  - [ ] Encodes discovered rules into the target pack's `SKILL.md` runbook.

### [REQ-FACT-008]: Local Sandbox Isolation
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL execute all test evaluations, script executions, and tool trial runs inside AutoReiv's local isolated sandbox (`EphemeralSandbox`).
- **Acceptance Criteria**:
  - [ ] Sandbox provisions an isolated temporary directory per evaluation pass.
  - [ ] Environment variables scrub sensitive tokens and host credentials.
  - [ ] Target file structures are mirrored as local mocks (e.g., sample `.ini` files, stub services).
  - [ ] Subprocess execution is capped with strict timeouts and memory limits.
  - [ ] Sandbox is automatically cleaned up after each test cycle unless preserved for debugging.

### [REQ-FACT-009]: 4-Stage Verification Battery
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL require all newly authored tools to pass an exhaustive 4-stage verification battery before registration into a User Agent Pack.
- **Acceptance Criteria**:
  - [ ] **Stage 1 (Deterministic Functional Execution)**: Automated test script executes against sandbox mock and exits with status code `0`.
  - [ ] **Stage 2 (Invariant & Safety Guardrails)**: Verifies that zero unauthorized path traversals, out-of-sandbox writes, or unapproved system commands were invoked.
  - [ ] **Stage 3 (Idempotency & Stress Replay)**: Tool is executed repeatedly with duplicate inputs, boundary values, and missing files without crashing or corrupting state.
  - [ ] **Stage 4 (SRE Critic Audit)**: Critic agent audits Python code for regex resilience, defensive type hints, exception handlers, and security hygiene.
  - [ ] Tool is rejected if any of the 4 stages fails, routing back to the Coder agent with detailed critique.

### [REQ-FACT-010]: Anti-Bloat Tool Consolidation Gate
- **Type**: State-Driven
- **EARS Statement**: WHILE designing and refining toolsets, THE SYSTEM SHALL consolidate related micro-actions into cohesive verb-action tools to prevent tool bloat.
- **Acceptance Criteria**:
  - [ ] Rejects the creation of fragmented single-verb tools (e.g., `start_service`, `stop_service`, `status_service` merged into `manage_service(action)`).
  - [ ] Enforces an upper ceiling of 3–6 active tools per specialist User Agent Pack.
  - [ ] Evaluates whether existing tools can be extended before authoring new tools.

### [REQ-FACT-011]: Automatic Agent Split Policy
- **Type**: State-Driven
- **EARS Statement**: WHILE evaluating agent scope, THE SYSTEM SHALL propose splitting the agent into multiple distinct User Agent Packs when responsibilities span disparate operational domains.
- **Acceptance Criteria**:
  - [ ] Triggers split proposal when tool count exceeds 8 or actions require conflicting permission tiers.
  - [ ] Generates two discrete `AgentProfile` blueprints with narrow, non-overlapping tool allowlists.
  - [ ] Creates a delegation contract between the split agents using `handoff_to_agent`.

### [REQ-FACT-012]: Durable Background Job Persistence
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL persist all training graph progress, packet stores, and execution states to SQLite, enabling jobs to safely survive application restarts.
- **Acceptance Criteria**:
  - [ ] Current graph node pointer and packet payload are persisted atomically per phase transition.
  - [ ] On application startup, queued and in-flight training jobs resume from their last completed node.
  - [ ] Training jobs can be paused, resumed, or aborted via REST API.

### [REQ-FACT-013]: Zero External Service Dependencies
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL execute the entire capability loop using local Python standard library and local LLMs without external cloud APIs or container daemons.
- **Acceptance Criteria**:
  - [ ] Runs hermetically on Windows with Python 3.12+ and SQLite WAL mode.
  - [ ] Utilizes local Ollama / LM Studio endpoints for all agent reasoning turns.
  - [ ] Operates without Docker, Kubernetes, or cloud vector database requirements.

### [REQ-FACT-014]: Human-In-The-Loop (HITL) Deployment Gate
- **Type**: State-Driven
- **EARS Statement**: WHILE deploying a trained agent to live environments, THE SYSTEM SHALL park destructive actions and out-of-lab promotions for human approval.
- **Acceptance Criteria**:
  - [ ] Promotion from lab catalog to live production roster creates a pending approval record.
  - [ ] Destructive tools (e.g., restore backup, delete instance) trigger a standard HITL approval card in Chat Studio.
  - [ ] Execution remains suspended in `waiting_approval` status until user clicks Approve or Reject.

### [REQ-FACT-015]: Automated Pack Scaffolding & Roster Registration
- **Type**: Event-Driven
- **EARS Statement**: WHEN all seed objectives pass the 4-stage verification battery, THE SYSTEM SHALL finalize the User Agent Pack in `$DATA_DIR/packs/<agent_id>/` and register it on the Agent Studio roster sheet.
- **Acceptance Criteria**:
  - [ ] Scaffolds complete `pack.json`, `tools/`, and `skills/` structure.
  - [ ] Initializes dedicated cognitive memory database (`<agent_slug>_memory.db`) with initial seed directives.
  - [ ] Displays completion summary in Chat Studio with verified tool list and test evidence.
  - [ ] Immediately makes the new agent selectable in Agent Studio and Chat Studio.

### [REQ-FACT-023]: Agent Studio Autonomous Training Controls
- **Type**: User-Initiated
- **EARS Statement**: WHEN configuring an agent in Agent Studio, THE USER SHALL have controls to enable "Allow Autonomous Training" and specify "Max Auto-Train Retries" (1–5, default 2), persisted across `pack.json`, `AgentProfile`, and SQLite database.
- **Acceptance Criteria**:
  - [ ] `#forgeAutoTrainCheckbox` toggles `allow_autonomous_training`.
  - [ ] `#forgeMaxTrainRetriesInput` sets `max_training_retries` bounded between 1 and 5.
  - [ ] Values persist across `pack.json`, `AgentProfile`, `agent_overrides`, and `custom_agents`.

### [REQ-FACT-024]: Turn-Time Missing Capability Detection & JIT Synthesis
- **Type**: Event-Driven
- **EARS Statement**: WHEN an agent encounters an operational request lacking required tools or capabilities during a chat turn, THE SYSTEM SHALL detect the deficiency and initiate in-flight JIT sandbox tool synthesis while streaming live `auto_train_progress` events.
- **Acceptance Criteria**:
  - [ ] `CapabilityDetector` identifies turn-time missing tool responses.
  - [ ] `AgentKernel` streams `auto_train_progress` events with stages (`synthesizing`, `sandbox_battery`, `deploying`, `completed`).
  - [ ] Chat Studio displays animated tool status indicator for auto-train stages.

### [REQ-FACT-025]: Strict 4-Stage Battery HITL Auto-Bypass
- **Type**: State-Driven
- **EARS Statement**: WHILE evaluating in-flight synthesized tools, THE SYSTEM SHALL auto-bypass the HITL deployment gate strictly when all four verification battery stages (Functional, Safety, Idempotency, Critic AST) pass 100% cleanly within the configured retry budget.
- **Acceptance Criteria**:
  - [ ] Auto-bypass requires 100% pass on all 4 stages of `VerificationBatteryService`.
  - [ ] If any stage fails, the synthesis loop retries up to `max_training_retries`.
  - [ ] If retries are exhausted, the tool is not deployed and the gap is logged to the backlog.

### [REQ-FACT-026]: Seamless Turn Resumption
- **Type**: Event-Driven
- **EARS Statement**: WHEN a synthesized tool is verified and registered in the agent pack, THE SYSTEM SHALL automatically resume the paused turn so the agent executes the newly registered tool and completes the user's original command seamlessly.
- **Acceptance Criteria**:
  - [ ] The agent kernel updates active tools and injects turn resumption context.
  - [ ] The agent calls the newly synthesized tool and generates the final user-facing response.
  - [ ] The entire flow completes without requiring a manual page reload or user re-prompt.

### [REQ-FACT-027]: SQLite Capability Gap Backlog Queue
- **Type**: State-Driven
- **EARS Statement**: WHEN a capability gap is detected for an agent with autonomous training disabled or after retries are exhausted, THE SYSTEM SHALL persist the gap in `agent_capability_gaps` and display it in the Agent Studio "Needs Training" backlog card.
- **Acceptance Criteria**:
  - [ ] SQLite table `agent_capability_gaps` records `id`, `agent_id`, `session_id`, `turn_text`, `identified_capability`, `suggested_tool_name`, `status`, and `created_at`.
  - [ ] Agent Studio displays `#agentTrainingBacklogCard` with badge count and gap items.
  - [ ] Each backlog item includes `[⚡ Train in Lab]` to trigger a training job and `[Dismiss]` to remove it.

### [REQ-FACT-028]: Chat Studio Training Action Trigger
- **Type**: User-Initiated
- **EARS Statement**: WHEN viewing assistant messages in Chat Studio, THE USER SHALL have a `[⚡ Train in Lab]` action button to immediately queue the capability gap and open the Lab training modal.
- **Acceptance Criteria**:
  - [ ] Assistant messages render `.train-lab-msg-btn` (`[⚡ Train in Lab]`).
  - [ ] Clicking the button calls `POST /api/agents/{agent_id}/gaps` and opens `#trainAgentHandshakeModal` pre-populated with context.

### [REQ-FACT-029]: Module-Qualified Host Cmdlet Tool Synthesis
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL author PowerShell operational tools and scripts with fully qualified module namespaces (e.g. `Hyper-V\<cmdlet>`) to prevent cmdlet shadowing by other installed system administration modules.
- **Acceptance Criteria**:
  - [x] All synthesized PowerShell cmdlets and scripts use `Hyper-V\<cmdlet>` prefix.

### [REQ-FACT-030]: Explicit Module Import in PowerShell Execution Runner
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL explicitly import the target module (e.g. `Import-Module Hyper-V -ErrorAction SilentlyContinue`) before executing host commands.
- **Acceptance Criteria**:
  - [x] `_run_powershell` in Python wrappers and PowerShell scripts prepend explicit module import.

### [REQ-FACT-031]: Cmdlet Namespace Collision Isolation and Clean Host Execution
- **Type**: Event-Driven
- **EARS Statement**: WHEN an agent executes host commands on the operator machine, THE SYSTEM SHALL execute exclusively against the intended target subsystem without intercepting foreign errors.
- **Acceptance Criteria**:
  - [x] `manage_hyperv(action="status")` executes cleanly against local Hyper-V with zero VMware PowerCLI error messages.

### [REQ-FACT-032]: Domain-Agnostic Purpose-Grounded Environment Discovery Probe
- **Type**: Event-Driven
- **EARS Statement**: WHEN the Lab discovery probe executes, THE SYSTEM SHALL ground inspection in the agent purpose to dynamically detect target execution medium (CLI, API, DB, Filesystem, Computation) and determine namespace isolation rules.
- **Acceptance Criteria**:
  - [x] `_step_discovery_probe` dynamically records target medium, discovered modules, and namespace isolation rules in `environment_manifest_json`.

### [REQ-FACT-033]: Verification Battery Stage 2 Environment Command Collision Guardrail
- **Type**: Event-Driven
- **EARS Statement**: WHEN the 4-stage verification battery evaluates a tool, THE SYSTEM SHALL inspect runtime stderr and reject tools that trigger foreign management module command collision signatures.
- **Acceptance Criteria**:
  - [x] Verification battery fails Stage 2 safety if collision signatures (`viserverconnectionexception`, etc.) are detected in stderr.

### [REQ-FACT-034]: Dedicated Factory Studio Primary Navigation
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL provide a top-level Factory Studio navigation control (`#tab-factory`, `#railBtnFactory`) in the desktop slim rail and sidebar navigation drawer with a `flask-conical` icon.
- **Acceptance Criteria**:
  - [x] Desktop app rail includes `#railBtnFactory` triggering Factory Studio.
  - [x] Sidebar navigation grid includes `#tab-factory` with `flask-conical` icon.
  - [x] Selecting Factory Studio smoothly displays `#view-factory` and updates ARIA active tab attributes.

### [REQ-FACT-035]: Two-Surface Factory Workspace (Pipeline & Prompts vs. Training Runs)
- **Type**: State-Driven
- **EARS Statement**: WHILE viewing Factory Studio (`#view-factory`), THE SYSTEM SHALL provide two sub-views (`#factoryTabPipelineBtn`, `#factoryTabRunsBtn`) allowing seamless toggle between the 8-stage visual flowchart with Phase Prompt Inspector and the Two-Pane Training Runs Monitor.
- **Acceptance Criteria**:
  - [x] Sub-view tab switcher allows switching between `#factoryPipelineView` and `#factoryRunsView`.
  - [x] Active sub-tab displays distinct visual selection indicators.
  - [x] State persists across tab switches within the studio session.

### [REQ-FACT-036]: Visual 8-Stage Flowchart with Phase Prompt Inspector
- **Type**: User-Initiated
- **EARS Statement**: WHEN an operator selects any of the 8 pipeline stages in the visual flowchart, THE SYSTEM SHALL display the stage's purpose description, status badge (`Platform Default` / `Custom Override`), read-only context variable helper pills, and an editable system prompt textarea with Save (`PUT`) and Reset (`DELETE`) actions.
- **Acceptance Criteria**:
  - [x] Visual flowchart renders all 8 phases: `intent_distill`, `ground`, `blueprint`, `author`, `scenario_verify`, `verify`, `optimize`, `promote`.
  - [x] Clicking any phase tile highlights it with active focus ring and loads its instructions into the inspector.
  - [x] Read-only context variable helper pills show available tokens; clicking a pill inserts it into prompt textarea.
  - [x] Saving updates custom instructions via `PUT /api/agent_training_factory/phases/{id}/instructions` and updates status badge.
  - [x] Reset restores built-in default via `DELETE /api/agent_training_factory/phases/{id}/instructions`.

### [REQ-FACT-037]: Dedicated Two-Pane Run Telemetry & HITL Deployment Gate
- **Type**: Event-Driven
- **EARS Statement**: WHEN an operator selects a training run in the Runs List pane, THE SYSTEM SHALL display its live 8-stage progress stepper, HITL deployment approval card (with Approve & Deploy / Reject actions), authored artifact pills with modal preview, and monospace streaming packet feed.
- **Acceptance Criteria**:
  - [x] Left pane displays scrollable runs list with search and status filtering (`All`, `Running`, `Done`, `Failed`, `Waiting Approval`).
  - [x] Right pane renders run header, 8-stage stepper showing run progress, artifact pills, and activity feed.
  - [x] When status is `waiting_approval`, prominent HITL action card provides Approve & Deploy to Fleet and Reject controls.
  - [x] Activity feed provides copy-to-clipboard button and packet count telemetry.

### [REQ-FACT-038]: Factory Studio Run Launch Wizard
- **Type**: User-Initiated
- **EARS Statement**: WHEN an operator clicks `[ 🚀 New Training Run ]` (`#factoryNewRunBtn`), THE SYSTEM SHALL present a launch wizard modal enabling agent selection, intent input, starter objectives, deliverable taxonomy, and launch a new job via `POST /api/agent_training_factory/jobs`.
- **Acceptance Criteria**:
  - [x] Header includes `[ 🚀 New Training Run ]` button.
  - [x] Launch modal allows selecting an agent or entering new agent ID, seed intent, and starter objectives.
  - [x] Submitting immediately dispatches training job, switches to Training Runs tab, and begins live polling.

### [REQ-FACT-039]: Mobile-Responsive Layout & Accessibility
- **Type**: Ubiquitous
- **EARS Statement**: THE SYSTEM SHALL render Factory Studio with responsive grid steppers, mobile view switching between run list and run details, touch-friendly tap targets, and WCAG AA contrast.
- **Acceptance Criteria**:
  - [x] Visual flowcharts and steppers reflow cleanly across mobile (`grid-cols-2 sm:grid-cols-4 lg:grid-cols-8`).
  - [x] On small viewports, runs list and run detail panes toggle smoothly with a Back button.
  - [x] ARIA attributes (`role="tab"`, `role="tabpanel"`, `aria-selected`) are fully synchronized.

### [REQ-FACT-040]: Factory Studio Agent Context Dropdown Selector
- **Type**: User-Initiated
- **EARS Statement**: WHEN viewing Factory Studio, THE SYSTEM SHALL provide an Agent Context Dropdown (`#factoryAgentSelect`) in the top navigation bar, allowing the operator to select either "All Agents" or a specific registered agent.
- **Acceptance Criteria**:
  - [x] Top bar renders `<select id="factoryAgentSelect">` alongside studio controls.
  - [x] Dropdown is dynamically populated with `All Agents (Platform View)` and all loaded agents from `/api/agents`.
  - [x] Selected agent persists in memory during studio navigation and updates the active context scope.

### [REQ-FACT-041]: Agent Context Filtered Telemetry & Pre-Scoped Launch
- **Type**: Event-Driven
- **EARS Statement**: WHEN an agent is selected in `#factoryAgentSelect`, THE SYSTEM SHALL automatically filter the training runs list to that agent, update status badge counts to reflect that agent's history, and pre-scope the `[ 🚀 New Training Run ]` action to that agent.
- **Acceptance Criteria**:
  - [x] Runs list displays only jobs matching the selected agent's ID.
  - [x] Status pill filters (All, In Progress, Needs Review, Completed, Failed) update counters to reflect the selected agent's jobs.
  - [x] Active runs badge (`#factoryActiveRunsBadge`) reflects active runs for the selected agent.
  - [x] Clicking `[ 🚀 Train Agent ]` launches `#trainAgentHandshakeModal` pre-populated with that agent's ID and name.

### [REQ-FACT-042]: Unified Training Hub Navigation & Agent Studio Shortcut
- **Type**: User-Initiated
- **EARS Statement**: WHEN an operator navigates from Agent Studio to train an agent or monitor training, THE SYSTEM SHALL transition the operator directly to Factory Studio with that agent pre-selected in `#factoryAgentSelect`.
- **Acceptance Criteria**:
  - [x] In Agent Studio (`#view-forge`), `#forgeTrainAgentBtn` ("Train in Lab") switches to Factory Studio with that agent selected.
  - [x] `#forgeLabMonitorBtn` switches to Factory Studio Runs view with that agent selected.
  - [x] Training lifecycle, monitoring, and HITL approvals are managed exclusively within Factory Studio.

### [REQ-FACT-043]: Explicit Target Agent Selector & Live Pack Indicator in Training Launcher
- **Type**: User-Initiated
- **EARS Statement**: WHEN opening `#trainAgentHandshakeModal`, THE SYSTEM SHALL provide an explicit Target Agent dropdown (`#trainAgentTargetSelect`) populated with registered agents and a `+ Create Brand New Agent...` option, alongside a live on-disk pack inspection indicator (`#trainAgentLiveInfo`) confirming target pack path, skill count, and tool count.
- **Acceptance Criteria**:
  - [x] `#trainAgentHandshakeModal` renders `<select id="trainAgentTargetSelect">` and `#trainAgentLiveInfo`.
  - [x] Dropdown is populated with all loaded agents and `__new__` (`+ Create Brand New Agent...`).
  - [x] Selecting an existing agent displays their on-disk pack info (`packs/<agent_id>/`), existing skills, and tools that will be augmented.
  - [x] Selecting `__new__` reveals `#trainAgentNameGroup` for authoring a new specialist role from scratch.
  - [x] Launching dispatches `target_agent_id` guaranteeing Ground, Blueprint, Author, and Promote execute against the chosen agent.

## CARD-172 extension

Intent Distill -> Ground -> Blueprint -> Author -> Scenario Verify -> Code Verify -> Optimize -> Promote. Inner rinse to Author; outer rinse to Intent Distill + Ground with Reflexion lessons. Domain-agnostic.
