# [CARD-165] Autonomous In-Flight Tool Synthesis, Agent Studio Auto-Train Controls, and Capability Gap Backlog

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: docs/specs/agent-pack-factory/
> **Labels**: `type:feature`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`

---

## 1. Why / Intent

Currently, when a user asks an agent to perform an action for which it lacks tools (e.g. asking Hyper-V *"can you create me a vm named 'billy'"*), the agent outputs conversational text explaining that it lacks command execution and provides PowerShell scripts for the user to run manually. The interaction ends with no record of the missing capability, requiring the human to manually formulate objectives and launch the training lab loop from scratch.

This card delivers the complete, self-improving capability loop:
1. **Per-Agent Autonomous Training Controls in Agent Studio**: A checkbox for **"Allow Autonomous Training"** (`allow_autonomous_training`) and a guardrail for **"Max Auto-Train Retries"** (`max_training_retries`, default 2, range 1–5).
2. **In-Flight JIT Tool Synthesis & Turn Resumption (When Enabled)**: When the agent detects it lacks a tool to satisfy the user's operational command, it pauses the turn, streams an informative progress indicator (`[⚡ Auto-Training in Progress: Synthesizing tool (Sandbox QA 1-4)...]`), authors and verifies the tool in the 4-stage sandbox battery, bypasses the deploy gate upon a 100% clean verification pass, hot-reloads the tool into the live agent registry, and **resumes** the user's turn to execute the action seamlessly.
3. **"Needs Training" Capability Gap Backlog (When Disabled)**: When auto-training is disabled, missing capabilities are saved into SQLite (`agent_capability_gaps`) and presented in an Agent Studio **"Needs Training"** backlog queue where the operator can accept, edit, or dismiss them with one-click pre-filled deliberate training.
4. **Chat Message Action**: A small **`[⚡ Train in Lab]`** action button below agent messages in Chat Studio allowing immediate capture of any turn into the training backlog.

---

## 2. What to Build

### A. Agent Studio Options & Model Schema (`src/web/templates/index.html`, `src/web/static/modules/studios/forge.js`, `src/application/agent_packs/schema.py`)
- Add **"Allow Autonomous Training"** checkbox (`#forgeAutoTrainCheckbox`) in Agent Studio under Agent Options (Card 1).
- Add **"Max Auto-Train Retries"** number input (`#forgeMaxTrainRetriesInput`, default 2, min 1, max 5) to guard against infinite development loops.
- Persist `allow_autonomous_training` (boolean, default false) and `max_training_retries` (int, default 2) in `pack.json` and `AgentProfile`.

### B. In-Flight JIT Capability Synthesizer & Turn Resumption (`src/application/kernel/agent_kernel.py`, `src/application/orchestration/factory_runner.py`)
- In `AgentKernel`: When execution recognizes that an operational prompt cannot be fulfilled due to missing tools:
  - If `agent.allow_autonomous_training is True`:
    1. Spawn an in-flight background factory job anchored to the active session.
    2. Stream JIT synthesis progress events (`event: auto_train_progress`) to the chat stream.
    3. Factory Runner executes Discovery -> Blueprint -> Toolmaker -> Sandbox Battery.
    4. Upon 100% clean 4-stage battery pass (AST audit, idempotency, safety, execution), automatically finalize the tool into `packs/<agent_id>/tools/` and reload `master_tool_registry` without stopping at the HITL gate.
    5. Re-invoke the turn with the newly registered tool present in the agent's tool definitions, completing the user's original request.
    6. Enforce retry ceiling: if battery fails after `max_training_retries` attempts, fall back to conversational response and log gap to backlog.

### C. "Needs Training" Capability Gap Backlog (`src/infrastructure/memory/repositories/capability_gaps.py`, `src/web/routers/gaps.py`, `src/web/static/modules/studios/forge.js`)
- SQLite table `agent_capability_gaps` tracking: `id`, `agent_id`, `session_id`, `turn_text`, `identified_capability`, `suggested_tool_name`, `status` (`pending`, `trained`, `dismissed`), `created_at`.
- Endpoints:
  - `GET /api/agents/{agent_id}/gaps`: List pending capability gaps for the agent.
  - `POST /api/agents/{agent_id}/gaps/{gap_id}/train`: Pre-populates and launches the Lab Loop for that gap.
  - `DELETE /api/agents/{agent_id}/gaps/{gap_id}`: Dismisses the gap.
- Agent Studio: Display a **"Needs Training"** card on the agent sheet with pending recommendations and **[Train in Lab]** / **[Dismiss]** buttons.

### D. Chat Studio Message Action Trigger (`src/web/static/modules/studios/chat.js`)
- Add **`[⚡ Train in Lab]`** button in the message footer (next to `[Workbench]` and `[Save to Wiki]`) on assistant messages that mention missing tools or capability limitations.
- Clicking it immediately logs the gap into the agent's backlog and presents a toast notification with a direct link to launch training.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] [REQ-FACT-023] Agent Studio includes `#forgeAutoTrainCheckbox` and `#forgeMaxTrainRetriesInput`, persisted in `pack.json` and `AgentProfile`.
- [x] [REQ-FACT-024] `AgentKernel` detects missing capabilities during execution; if auto-training is enabled, initiates JIT synthesis and streams progress.
- [x] [REQ-FACT-025] In-flight synthesis bypasses HITL deploy gate strictly when all 4 stages of the sandbox verification battery pass cleanly, bounded by `max_training_retries`.
- [x] [REQ-FACT-026] Paused chat turn automatically resumes with the newly registered tool in hand, executing the tool and answering the user's prompt.
- [x] [REQ-FACT-027] When auto-training is disabled, gaps are persisted to `agent_capability_gaps` and displayed in Agent Studio's "Needs Training" backlog.
- [x] [REQ-FACT-028] Chat Studio features `[⚡ Train in Lab]` action on assistant turns to manually queue turns for training.
- [x] Unit tests in `tests/unit/kernel/test_in_flight_synthesis.py` verifying detection, sandbox pass, and turn resumption.
- [x] Frontend Vitest tests in `tests/unit/frontend/auto_train_backlog.test.js` verifying DOM controls and backlog queue.
- [x] Full test suites green (`pytest` and `npm run test:unit:frontend`), zero lint errors.

---

## 4. Constraints & Honor Flags

- **Deterministic Sandbox Gate**: In-flight auto-training only bypasses HITL if the tool passes 100% of the 4-stage sandbox battery (Stage 1 Functional, Stage 2 Safety & Path Traversal, Stage 3 Idempotency, Stage 4 AST Critic). If any stage fails, HITL is never bypassed.
- **Strict Bounded Retries**: The loop must terminate if the coder cannot pass the sandbox within `max_training_retries`.
- **Zero OS Mutations in Training**: All tool synthesis happens strictly inside `EphemeralSandbox`.
