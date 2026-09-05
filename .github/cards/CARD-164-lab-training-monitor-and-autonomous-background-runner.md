# [CARD-164] Lab Training Monitor and Autonomous Background Runner

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:feature`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.HITL`

---

## 1. Why / Intent

When users train an agent in the lab (such as clicking **"Train in Lab"** on Hyper-V in Agent Studio), the training job is saved in SQLite (`factory_jobs`), but no background worker actively advances the training graph, and the user has no UI surface to monitor progress, view live stage transitions, or interact with the deployment gate.

Furthermore, training jobs currently latch onto whatever chat session was active in the background. Because new agents or headless agents may not even appear in the chat picker (`show_in_chat: false`), HITL deployment prompts can easily be orphaned.

This card delivers:
1. **The Autonomous Factory Runner Engine**: A background worker in the application lifespan that polls queued/running factory jobs and executes the deterministic capability graph (Inspection -> Blueprint -> Toolmaker -> Sandbox Battery -> SRE Critic -> HITL Deploy Gate).
2. **AutoReiv Platform Chat Anchoring**: All training lifecycle milestones and the final **Approve & Deploy** HITL card are pinned directly to the **AutoReiv platform agent's** chat session, ensuring a permanent and reliable home for fleet management.
3. **The Lab Monitor Drawer in Agent Studio**: A slide-over monitoring drawer in Agent Studio showing active/recent training runs, a 5-stage visual stepper, live activity logs (packets), and direct Approve & Deploy controls.

---

## 2. What to Build

### A. Backend Factory Runner Engine (`src/application/orchestration/factory_runner.py`)
- Background async worker `FactoryRunner` registered in `src/web/app.py` lifespan (similar to `RoutineScheduler`).
- Periodically checks for `factory_jobs` with status `queued` or `running`.
- Drives the job through the capability loop:
  - `discovery_probe`: Executes environment inspection via `EnvironmentInspectionTools` and compiles `EnvironmentManifest`.
  - `architecture_blueprint`: Evaluates tool consolidation heuristics (targeting 3–6 tools) and generates seed tool specs.
  - `coder_node`: Authors tool code (`packs/<agent_id>/tools/<tool>.py`) and SOP runbooks (`SKILL.md`).
  - `sandbox_battery_node`: Runs the 4-stage verification battery (`VerificationBatteryService`) inside `EphemeralSandbox`.
  - `critic_signoff_node`: Verifies clean AST audit, zero safety violations, and generates `PromotePacket`.
  - `hitl_deploy_gate_node`: Sets status to `waiting_approval` and registers a pending deployment approval.
- Emits structured progress packets to `factory_packets` at each node transition.

### B. AutoReiv Platform Session Anchoring (`src/web/routers/factory.py`, `src/web/static/modules/studios/chat.js`)
- When creating a factory job (`POST /api/factory/jobs`), if no explicit `session_id` is passed or if initiated from Agent Studio, automatically resolve or create a session under the **`autoreiv`** platform agent.
- In AutoReiv's chat, post the live training status card.
- When the job reaches `waiting_approval`, post the **Approve & Deploy** promotion card directly in AutoReiv's chat feed.
- Clicking **Approve & Deploy** calls `POST /api/factory/jobs/{job_id}/promote`, finalizes the pack into `$DATA_DIR/packs/<agent_id>/`, imports it into the live agent registry, and marks the job `done`.

### C. Lab Monitor Drawer in Agent Studio (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`)
- Add **"Lab Monitor"** button (`#forgeLabMonitorBtn`) next to "Train in Lab" in Agent Studio header with a badge showing active runs count (`#forgeLabRunsBadge`).
- Slide-over drawer `#labMonitorDrawer` displaying:
  - Header with close button and active run filter.
  - Active Run Card:
    - Target Agent name and icon.
    - **5-Stage Stepper**:
      1. `Discovery` (Inspection)
      2. `Blueprint` (Consolidation & Specs)
      3. `Toolmaker` (Authoring)
      4. `Sandbox Battery` (4-Stage Verification)
      5. `Review & Deploy` (HITL Gate)
    - **Live Packet Activity Feed**: Auto-scrolling terminal/log box showing real-time messages from Inspector, Coder, Sandbox, and Critic.
    - **Actions**: "Approve & Deploy" and "Reject" buttons when in `waiting_approval`.
  - Polling / Event hook: Periodically refreshes active job status every 3 seconds while drawer is open.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] [REQ-FACT-016] `FactoryRunner` background worker implemented and started in `create_app` lifespan in `src/web/app.py`.
- [x] [REQ-FACT-017] Factory runner advances queued jobs through all graph nodes to `hitl_deploy_gate_node` without human intervention during sandbox testing.
- [x] [REQ-FACT-018] All training jobs initiated from Agent Studio or Chat are anchored to the `autoreiv` platform agent's session for HITL review.
- [x] [REQ-FACT-019] Agent Studio features `#forgeLabMonitorBtn` and `#labMonitorDrawer` showing stage stepper, live packet logs, and approval buttons.
- [x] [REQ-FACT-020] Clicking "Approve & Deploy" in either AutoReiv's chat or the Lab Monitor drawer finalizes the agent pack and reloads the registry cleanly.
- [x] [REQ-FACT-021] Unit tests in `tests/unit/orchestration/test_factory_runner.py` verifying end-to-end background runner state progression.
- [x] [REQ-FACT-022] Frontend Vitest contract tests verifying `#labMonitorDrawer` DOM elements, badge counts, and stepper updates.
- [x] Automated tests green via `pytest tests/unit/`.
- [x] Frontend tests green via `npm run test:unit:frontend`.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- **Zero live OS mutations during training**: All tool testing strictly occurs within `EphemeralSandbox`.
- **Strict User Pack Isolation**: Generated tools and runbooks are written strictly to `$DATA_DIR/packs/<target_agent_id>/`.
- **Local Model Economy**: Local models only receive the focused context of the active role.
- Single isolated `feat/card-164-lab-training-monitor` branch cut from `qa`.
- Card remains **Ready** until the human visionary explicitly approves and says build.
