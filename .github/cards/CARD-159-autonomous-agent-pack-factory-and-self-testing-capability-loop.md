# [CARD-159] Autonomous Agent Pack Factory and Self-Testing Capability Loop

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:architecture`, `type:spec`, `AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, `AutoReiv.Agents`

---

## 1. Why / Intent

Users want AutoReiv to be able to autonomously create, train, test, and optimize new specialist agents (e.g., Linux Game Server Host, Personal Finance, HomeLab Sysadmin) without requiring manual Python coding, schema design, or prompt engineering.

Users operating substantial local hardware (e.g. 128GB unified memory running Ollama 32B/72B models) have essentially free, unlimited compute for overnight execution. Rather than inventing brittle tools on the fly during live chat turns, AutoReiv will run an **autonomous overnight capability loop (The Factory in a Lab)** that discovers environment details, writes focused tools, runs them against sandbox mocks, consolidates bloat, and verifies correctness through an exhaustive multi-stage battery.

### Core Architectural Separation
- **The Factory Team (Core Platform Packs in `platform-packs/`)**: Built-in specialist roles (Conductor, Inspector, Coder, Sandbox Runner, SRE Critic) with `show_in_chat: false` by default so they do not clutter chat menus.
- **The Output (User Agent Packs in `$DATA_DIR/packs/<agent_id>/`)**: The factory authors and tests tools, runbooks, and definitions strictly inside self-contained, portable User Agent Packs.
- **Pack Scoping & Local Model Economy**: Tools belong to the specific agent pack being trained. Local models never see massive global tool registries; they receive only the 3–6 tools strictly relevant to their role.

---

## 2. Core Architecture & Primitives

### 1. The Factory Specialist Roles
1. **Conductor / Architect (`platform-packs/conductor/`)**:
   - Manages the training graph, tracks seed goals, routes work between roles, and commits verified tools to the target user pack.
   - Tools: Scoped exclusively to delegation and pack registration (`handoff_to_agent`, `register_pack_tool`). Does *not* write code or run commands directly.
2. **Inspector / Discovery (`platform-packs/inspector/`)**:
   - Executes safe, read-only discovery on target hosts, directories, and endpoints.
   - Extracts file layouts, runtime configurations (systemd, docker, ini, yaml), process states, and log paths.
   - Compiles structured **Environment Manifests** and pulls domain Standard Operating Procedures (SOPs).
3. **Coder / Toolmaker (`platform-packs/coder/`)**:
   - Authors and refines atomic Python tools (`packs/<agent_id>/tools/<tool_name>.py`) and runbooks (`SKILL.md`).
   - Tools: Scoped exclusively to file writing and editing (`write_pack_tool`, `edit_pack_tool`).
4. **Sandbox Runner / QA (`platform-packs/sandbox_runner/`)**:
   - Sets up mock environments (mirrored config files, stub services) in AutoReiv's local isolated sandbox (`EphemeralSandbox`).
   - Executes newly authored tools and test runners against the sandbox, returning raw outputs and exit codes.
   - Tools: Scoped exclusively to sandbox execution (`run_sandbox_command`, `read_sandbox_file`).
5. **SRE Critic / Auditor (`platform-packs/critic/`)**:
   - The skeptical reviewer. Audits tool code for edge cases, error handling, unhandled exceptions, and security vulnerabilities.
   - Reviews test logs and verifies invariant safety properties before giving sign-off.

### 2. Packets: Structured Inter-Room Communication
Workers and the Conductor do not exchange messy, token-heavy conversation transcripts. They communicate via typed, structured packets stored in SQLite:
- **WorkPacket**: Goal description, environment facts, operational constraints, Definition of Done.
- **GapPacket**: Identified capability gap (`tool` | `skill` | `agent` | `graph_edge`), justification, evidence, proposed signature.
- **EvalPacket**: Test battery executed, pass/fail status, stdout/stderr, coverage metrics.
- **PromotePacket**: Diffs of authored tools/skills, benchmark scores, security sign-offs, and human approval status.

### 3. The 4-Stage Verification Battery (Zero Hallucinations)
To guarantee correctness during unattended overnight runs, newly drafted tools must pass all four stages before registration:
1. **Stage 1: Deterministic Functional Execution**: Automated test script exits with status code `0` against the sandbox mock.
2. **Stage 2: Invariant & Safety Guardrails**: Verified that no unauthorized filesystem access, path traversal, or out-of-scope system modifications occurred.
3. **Stage 3: Idempotency & Stress Replay**: Re-running the tool multiple times (including with dirty/edge-case inputs and missing files) produces consistent results without crashing or corrupting state.
4. **Stage 4: SRE Critic Audit**: The Critic agent audits the Python code structure, regex resilience, type signatures, and defensive error handlers.

### 4. Anti-Bloat & Consolidation Policies
- **Tool Consolidation Gate**: Discourage micro-tool proliferation. Merge related actions into cohesive verb-action tools (e.g. `manage_service(action='status'|'start'|'stop')` instead of 3 separate tools), targeting 3–6 tools per agent pack.
- **Split Policy**: If an agent's responsibilities cross distinct administrative or domain boundaries (e.g. game server management vs. network firewall routing), the Conductor automatically proposes splitting the workload into two distinct, focused agent packs.

### 5. User Interaction & Workflow
1. **Request in Chat**: User asks AutoReiv for a new agent and checks **`[x] Train Agent`**.
2. **30-Second Socratic Handshake**: AutoReiv presents 2–3 structured multiple-choice options (Target host/directory, Top 3 desired tasks, Risk/HITL policy).
3. **Overnight Background Execution**: Job is tracked durably in SQLite (`jobs`, `phases`, `packets`). Runs autonomously in the background and safely survives system restarts.
4. **Morning Delivery**: Finished User Agent Pack is verified, packaged in `$DATA_DIR/packs/<agent_id>/`, and loaded onto the Agent Studio roster with clear QA documentation.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] Core Factory Agent Packs created under `platform-packs/` with `show_in_chat: false` (Conductor, Inspector, Coder, Sandbox Runner, Critic).
- [x] Structured Packet models (`WorkPacket`, `GapPacket`, `EvalPacket`, `PromotePacket`) and SQLite storage tables implemented.
- [x] Graph-based Job/Phase Orchestrator with conditional edge branching (`ok`, `fail`, `need_capability`, `need_human`).
- [x] Read-only environment inspection and manifest generation tools implemented.
- [x] 4-stage automated verification battery implemented and integrated into the capability loop.
- [x] Tool consolidation and agent split policy heuristics enforced prior to pack finalization.
- [x] Chat Studio UI extended with "Train Agent" option and Socratic handshake interaction.
- [x] All new components covered with 100% green unit and integration tests.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags
- **Strict User Pack Isolation**: The factory must write generated tools and skills exclusively into the target User Agent Pack (`$DATA_DIR/packs/<agent_id>/`), never polluting platform directories.
- **Sandbox Safety**: All execution testing during the capability loop must occur inside isolated sandboxes. Zero unverified mutations on live target machines.
- **Zero Third-Party Trademarks**: No proprietary product or character names in codebase or card artifacts.
- Zero breaking changes to existing test suites.
