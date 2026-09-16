# [CARD-337] Granular Telemetry Attribution, Direct Agent & Performance Audit Routine

> **Status**: In Review
> **Created**: 2026-09-16
> **Spec Reference**: docs/specs/granular-telemetry-and-performance-audit/
> **Labels**: `type:feature`, `domain:telemetry`, `domain:observability`, `domain:agents`

---

## 1. Why / Intent

AutoReiv's agent harness injects persona instructions, complete JSON tool schemas, progressive skill metadata, and episodic memory facts on every turn. While powerful, this "harness tax" can expand a 60-token user prompt into 5,000 tokens of input, severely increasing Time-To-First-Token (TTFT), KV-cache pressure on local hardware (Nvidia Spark, Nimo PC), and token costs on cloud models.

Currently, `telemetry_spans.prompt_tokens` logs only a single lump-sum number. Operators cannot pinpoint which layer is causing bloat (tool schemas vs. memory vs. persona vs. tool results), nor can they run a pure, zero-tool baseline conversation.

This card delivers:
1. A built-in **`direct`** platform agent with zero tools and zero skills for pure model baselines and fast, cheap chat.
2. **Granular Telemetry Attribution** logged on every turn span, isolating exact token counts for every prompt component (user, persona, tools, skills, memory, tool dumps) and timing stages (prep, TTFT, generation, inter-step).
3. A **Performance & Cost Audit** capability for the `autoreiv` platform agent that inspects any `job_id`, `session_id`, or historical window, formats a comprehensive efficiency report, and hands off to the Wiki agent to publish directly to Wiki Studio.
4. A pre-configured **Routine** to automate this audit on a recurring schedule.

---

## 2. What to Build

### 1. Platform `direct` Agent
- Add built-in platform agent manifest `direct` (under `platform-packs/` / user data):
  - `tools: []` (no tools mounted, not even default system-wide tools).
  - `skills: []` (no progressive skills loaded).
  - `system_prompt: "You are a direct, concise assistant."`
  - Visible in Chat Studio agent selector.

### 2. Granular Token & Timing Telemetry in `AgentKernel`
- At request construction in `agent_kernel.py`, calculate token attribution for each discrete component:
  - `user_prompt`: Raw user input characters/tokens.
  - `agent_persona`: System prompt / constitution tokens.
  - `tool_schemas`: Function declaration JSON schema tokens.
  - `progressive_skills`: Injected skill headers and bodies.
  - `episodic_memory`: Recalled facts from memory store.
  - `compacted_history`: Prior message turns in window.
  - `tool_results_injected`: Raw tool output payload tokens.
  - `completion`: Output tokens generated.
  - `reasoning`: Reasoning/thinking tokens generated (when supported).
- Measure timing breakdown:
  - `harness_prep_ms`: Wall-clock time spent compacting and assembling payload.
  - `ttft_ms`: Time to first token from provider.
  - `generation_ms`: Time from first token to stream close.
  - `tokens_per_second`: Effective generation speed.
  - `inter_step_latency_ms`: In multi-phase jobs, latency between phase $N$ completion and phase $N+1$ launch.
- Persist this structured breakdown into `telemetry_spans.metadata_json` on every turn.

### 3. `audit_performance_and_cost` Skill & Tool for `autoreiv` Agent
- Tool callable by the `autoreiv` control-plane agent.
- Accepts parameters: `job_id: Optional[str]`, `session_id: Optional[str]`, `hours: Optional[int]`.
- Reads `telemetry_spans` and formats a structured Markdown report:
  - Component token breakdown table and percentages.
  - TTFT, generation speed, and total latency.
  - Cost analysis (scaffold cost vs user input cost vs completion cost).
  - Flags actionable bloat warnings (e.g. tool schemas > 60% of context).
- Hands off to Wiki agent (`librarian` / `wiki_save_page`) to persist to `wiki/01_Engineering/Performance/`.

### 4. Automated Performance Audit Routine
- Pre-configured Routine definition (`Daily Performance & Cost Audit`):
  - Agent: `autoreiv`
  - Prompt: `"Audit performance and cost for all jobs in the last 24 hours and publish the report to the Wiki."`
  - Default cron: `0 2 * * *` (2:00 AM daily).

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `direct` agent appears in agent list with zero tools and zero skills.
- [ ] Running a turn with `direct` results in `metadata_json` recording 0 tool schema tokens and near-zero scaffold overhead.
- [ ] Standard turns with `assistant` record granular token attribution (`user_prompt`, `tool_schemas`, `agent_persona`, `episodic_memory`, `skills`) in `telemetry_spans.metadata_json`.
- [ ] Turn timing metrics (`harness_prep_ms`, `ttft_ms`, `generation_ms`, `tokens_per_second`) are accurately recorded in `metadata_json`.
- [ ] Asking `autoreiv` to "audit performance for job <id>" or "audit performance for the last 24 hours" invokes the audit tool, computes the granular report, and saves it into Wiki Studio.
- [ ] Automated unit tests passing via `pytest tests/unit/telemetry/` and `tests/unit/kernel/`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing `telemetry_spans` schema (`metadata_json` carries the new payload).
- No hardcoded external tokenizers; robust fast approximation (`len(text) // 4` or standard token counter) with zero latency impact.
- Standard SDLC hygiene: `feat/*` branch cut from `qa`.
