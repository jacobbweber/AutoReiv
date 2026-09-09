# [CARD-204] Promote Goal and Verify to Pure Chat Runtimes and Retire Redundant Platform Skills

> **Status**: In Review
> **Created**: 2026-09-09
> **Spec Reference**: none
> **Labels**: `type:architecture`, `type:cleanup`, `type:refactor`, `in-review`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
1. **Clarify Chat Runtimes vs. Agent Tools**:
   - **Goal Mode** and **Self-Verify** belong where users actually interact with them: as **Runtime Modes** in Chat Studio's Options drawer (`#chatOptionsDrawer`).
   - They do not belong as confusing, redundant checkboxes in Agent Studio Box 1 (**Platform Skills & Tools**).
2. **Retire `planning` and `verification` from Box 1**:
   - Remove "Goal Planning Engine" (`planning`) and "Logic Verification (Critic)" (`verification`) from Platform Skills in Agent Studio.
   - When a user inspects Box 1 on any agent, they will only see the 5 genuine platform tool suites:
     1. **Wiki & Knowledge Vault** (`wiki`)
     2. **Agent Coordination & Handoff** (`coordination`)
     3. **Capability Proposals & Discovery** (`proposals`)
     4. **Batch Worker & Artifacts** (`worker`)
     5. **Isolated Code Sandbox** (`sandbox`)
     (Plus the runbook `build-agent-pack`).
3. **Keep Chat Studio Goal and Self-Verify 100% Functional**:
   - Toggling **Goal** in Chat Studio continues to formulate multi-phase jobs via `PlanEngine` and `JobOrchestrator`, requiring Human-in-the-Loop review and displaying live step progress.
   - Toggling **Self-Verify** in Chat Studio continues to run the `ReflexionLoopEngine` critic on turns and job phases.
4. **Clean Up AppData & Profiles**:
   - Safely prune `planning/` and `verification/` runbook directories from `%LOCALAPPDATA%\AutoReiv\skills\`.
   - Ensure existing agent profiles in SQLite and seeds no longer inject dead tool schemas (`formulate_plan`, `get_active_plan`, `assert_json_schema`, etc.) into LLM system prompts.

---

### Beat 2: What AutoReiv Does Now
1. **Confusing Redundant Skills in Box 1**:
   - In `src/application/agent_packs/schema.py:L84-96`, `PLATFORM_SKILL_TOOLS` includes `"planning"` and `"verification"`.
   - In `src/infrastructure/data/resolver.py:L142`, `PLATFORM_SKILL_SEEDS` seeds `planning` and `verification` into `$DATA_DIR/skills/`.
   - In Agent Studio Box 1, users see checkboxes for "Goal Planning Engine" and "Logic Verification (Critic)". Checking them adds tools (`get_active_plan`, `append_plan_step`, `assert_json_schema`, `validate_metric_bounds`) to `agent.allowed_tool_names`, wasting prompt tokens on every turn.
   - `formulate_plan` is advertised in the schema but was never implemented as a callable tool in `PlanningTools.register_tools`.
2. **Independent Server Runtimes**:
   - In `src/web/routers/chat.py:L1114-1183`, `goalMode: true` triggers `plan_engine.formulate_plan` and `persist_plan_as_job` on the server. It never uses the agent's `PlanningTools`.
   - In `src/web/routers/chat.py` and `src/application/kernel/reflexion_engine.py`, `selfVerify: true` runs `ReflexionLoopEngine` (built-in critic or dynamic tool injection). It never depends on whether `verification` was checked on the agent profile.

---

### Beat 3: What Will Change
1. **Schema & Seed Simplification**:
   - In `src/application/agent_packs/schema.py`:
     - Remove `"planning"` and `"verification"` from `PLATFORM_SKILL_TOOLS` and `PLATFORM_SKILL_METADATA`.
     - Platform skills tuple `PLATFORM_SKILL_IDS` becomes: `("wiki", "coordination", "proposals", "worker", "sandbox")`.
   - In `src/infrastructure/data/resolver.py`:
     - Remove `"planning"` and `"verification"` from `PLATFORM_SKILL_SEEDS`.
     - Add `"planning"` and `"verification"` to `prune_bled_platform_skills` so existing AppData directories are cleaned up automatically.
2. **Agent Studio UI Box 1**:
   - Box 1 in Agent Studio will cleanly render only the 5 active, callable platform tool suites.
   - Profile saver in `forge.js` and backend will no longer store `planning` or `verification` in `allowed_tool_names` or `allowed_skill`.
3. **Chat Studio Verification**:
   - Verify that Chat Studio's `Goal` toggle and `Self-Verify` toggle operate cleanly without any regression.
4. **Automated Test Updates**:
   - Update tests in `tests/unit/agent_packs/` and `tests/unit/skills/` to reflect the clean 5 platform skills.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] **AC-1 (Box 1 Cleanliness)**: In Agent Studio, Box 1 displays strictly the 5 core platform skills (`wiki`, `coordination`, `proposals`, `worker`, `sandbox`). Zero references to `planning` or `verification` appear.
- [x] **AC-2 (Platform Seeds Synchronized)**: `PLATFORM_SKILL_IDS` in `schema.py` and `PLATFORM_SKILL_SEEDS` in `resolver.py` contain only the 5 active platform skills (plus `build-agent-pack` runbook).
- [x] **AC-3 (AppData Pruned)**: On startup, `bootstrap_data_dir` safely removes `skills/planning/` and `skills/verification/` from `%LOCALAPPDATA%\AutoReiv\skills\`.
- [x] **AC-4 (Chat Studio Goal Intact)**: Toggling **Goal** in Chat Studio correctly formulates a multi-phase job, presents the approval modal, and executes all phases upon approval.
- [x] **AC-5 (Chat Studio Self-Verify Intact)**: Toggling **Self-Verify** in Chat Studio correctly executes the `ReflexionLoopEngine` critic pass on generated answers.
- [x] **AC-6 (No Phantom Tokens)**: Agent turn requests never include schema definitions for `get_active_plan`, `mark_plan_step_completed`, `append_plan_step`, `assert_json_schema`, or `validate_metric_bounds`.
- [x] **AC-7 (Automated Tests Passing)**: All test suites (`pytest tests/unit/agent_packs/`, `pytest tests/unit/skills/`, `pytest tests/unit/web/`, `npx vitest run`) pass cleanly.
- [x] **AC-8 (Lint & Quality)**: Zero ruff lint errors (`ruff check .`).

---

## 3. Constraints & Invariants
- Follows the working agreement in `AGENTS.md`.
- No code written until Jacob approves this card with "build".
- Local `qa` branch workflow. Zero push, tag, or merge to `main`.

