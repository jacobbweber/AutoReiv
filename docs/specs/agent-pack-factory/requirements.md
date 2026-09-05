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
