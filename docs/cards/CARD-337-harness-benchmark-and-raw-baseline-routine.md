# [CARD-337] Granular Telemetry Attribution, Direct Agent & Observe Studio Performance Audit

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
3. An interactive **Harness & Telemetry Audit View in Observe Studio**: pick an agent and chat session to inspect granular attribution, harness tax ratios, latency, and costs, with a one-click **"Generate Report"** button exporting formatted markdown directly into `00_Inbox/` with $0.00 LLM cost.

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

### 3. Observe Studio Audit Endpoints & Interactive UI
- Backend REST endpoints in `src/web/routers/observability.py`:
  - `GET /api/observability/sessions?agent_id=<id>`: List recent sessions for an agent.
  - `GET /api/observability/audit?session_id=<id>`: Deterministically compute token attribution, harness tax, latencies, and costs via `AuditService`.
  - `POST /api/observability/audit/export`: Export pre-formatted markdown report directly to `00_Inbox/<slug>.md` honoring the One-Door Policy.
- Observe Studio UI in `src/web/templates/index.html` and `src/web/static/modules/studios/observability.js`:
  - Session dropdown dynamically populated when selecting an agent.
  - Granular telemetry audit card rendering Scaffold Ratio, Prompt/Completion breakdown, TTFT/TPS, bloat warnings, and full component table.
  - "Generate Report to Inbox" button for instant one-click markdown filing.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `direct` agent appears in agent list with zero tools and zero skills.
- [x] Running a turn with `direct` results in `metadata_json` recording 0 tool schema tokens and near-zero scaffold overhead.
- [x] Standard turns with `assistant` record granular token attribution (`user_prompt`, `tool_schemas`, `agent_persona`, `episodic_memory`, `skills`) in `telemetry_spans.metadata_json`.
- [x] Turn timing metrics (`harness_prep_ms`, `ttft_ms`, `generation_ms`, `tokens_per_second`) are accurately recorded in `metadata_json`.
- [x] In Observe Studio, selecting an agent and a session displays the granular token attribution breakdown, scaffold ratio, and timing stats.
- [x] Clicking "Generate Report to Inbox" saves the formatted markdown file directly into `00_Inbox/` without burning LLM inference tokens.
- [x] Automated unit tests passing via `pytest tests/unit/observability/` and `npm run test:unit:frontend`.
- [x] Zero lint errors via `ruff check` and `npm run lint:frontend`.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing `telemetry_spans` schema (`metadata_json` carries the new payload).
- No artificial LLM reasoning loops for deterministic telemetry data.
- One-Door Policy honored: all exports land in `00_Inbox/`.
- Standard SDLC hygiene: `feat/*` branch cut from `qa`.
