# Comparative Architecture Review: AutoReiv vs. Crucible vs. Agent-OS

> **Card**: `CARD-698` (Milestone M29)  
> **Scope**: Side-by-side architectural and product comparison of **AutoReiv** (`/home/spark/autoreiv`), **Crucible** (`/home/spark/projects/crucible`), and **Agent-OS** (`/home/spark/projects/Agent-OS`), with ranked **Adopt / Adapt / Skip** recommendations and concrete next-milestone options.

---

## 1. Executive Summary & Side-by-Side Matrix

The three repositories represent three distinct points in the design space of a local-first, self-evolving personal AI operating system:

- **AutoReiv** is a full-stack, production-grade web + FastAPI local companion system with a 3-agent roster (`AutoReiv`, `Tutor`, `Direct`), Agora folder-based skill authoring (`SKILL.md` + `scripts/` + `references/`), unified Capabilities Studio, hardware-gated routines, Wiki + FTS5 knowledge base, SRS education, and a live browser QA harness (`live_qa.py`).
- **Crucible** is an experimental, feature-dense `agent_os` prototype exploring 15 ADRs (`ADR-0001` through `ADR-0015`): dual-channel continuum (`companion_front_door.py` + background `RecipeChamber`), hot/cold SQLite session partitioning (`ADR-0009`), local MELT telemetry with RCA proposal staging into `00_Inbox` (`ADR-0008`), and contract-first ingredients (`ADR-0014`, `ADR-0015`) with capability signatures and runtime autonomy modes (`autonomous` / `balanced` / `strict`).
- **Agent-OS** is a clean-sheet, zero-dependency Python 3.11+ core built around three explicit principles: **P1 Portability**, **P2 Chat as the Control Surface**, and **P3 Code Owns Control (the model fills steps and its output is checked)**. Its initial slices (`turn.py`, `compaction.py`, `retention.py`, `recipes.py`, `trace.py`, `local_setup.py`) demonstrate deterministic post-checks on model outputs, lossless hot/cold archiving with `archive_links`, OpenTelemetry-aligned per-turn JSONL span waterfalls, and zero-friction local port probing.

| Dimension | AutoReiv (`/home/spark/autoreiv`) | Crucible (`/home/spark/projects/crucible`) | Agent-OS (`/home/spark/projects/Agent-OS`) |
|---|---|---|---|
| **Primary Surface** | Responsive Web UI (Chat, Capabilities, Routines, Wiki, Tutor, Models, Settings) + FastAPI API | CLI (`agent-os chat/serve/status`) + lightweight FastAPI Web UI | Terminal CLI (`python -m agent_os`, `./run.sh`, `traces`, `trace <turn_id>`) |
| **Agent Roster** | 3 shipped agents (`AutoReiv` companion/builder, `Tutor`, `Direct`) + user agents | Single lifelong companion front door + anonymous ephemeral sandbox workers | Single companion core + planned isolated OS-process workers |
| **Capability Unit** | **Skill folder** (`SKILL.md` runbook + `tools:` frontmatter + `scripts/` + `references/`) + **Tools** (Python or MCP) | **Declarative Recipe** & **Ingredient Contracts** (`tool`, `context_source`, `model_profile`, `runbook`, `recipe`) | **Recipe folder** (`recipes/<id>/CONTEXT.md` with `When to use`, `Inputs`, `Process`, `Outputs`) executed by code |
| **Tool Scoping** | Single lever `resolve_allowed_tools(agent)` (`ADR-0061`) + per-turn session skill narrowing (`CARD-688`) + 15-tool cap (`ADR-0054`) | `ADR-0011` zero-catalog semantic triage $\rightarrow$ `ADR-0015` structured `TaskIntent` + ONNX `bge-small` recall + schema bind gate | Tiny catalog line per recipe in system context; code runs the recipe and validates inputs/outputs |
| **Compaction & History** | Context compaction in SQLite (`autoreiv.db`); active session list + session deletion (`CARD-696`) | `ADR-0009` hot `sessions.db` ($\le 90$ days) + cold `sessions_archive.db` ($> 90$ days) + `session_search_history` with provenance badges | `compaction.py` token-verified 3-section summary (`Decisions`, `Open tasks`, `Key facts`) + `archive_links` + `retention.py` verified hot-to-cold move |
| **Observability** | Job cards, audit logs, LLM call logging in SQLite, `/api/health` | `ADR-0008` `telemetry.db` (MELT) + self-monitoring recipes + staged RCA proposals in `00_Inbox/` | `trace.py` per-turn JSONL span waterfall (`data/traces/<turn_id>.jsonl`) + CLI `trace <id> [--full]` + optional OTLP export (`otlp.py`) |
| **Autonomy & Governance** | `AUTOREIV_APPROVAL_MODE` (`strict` vs `hands_off` in `CARD-691`) + pending tool approvals + sandbox AST validation | `ADR-0015` 3-tier runtime `ApprovalMode` (`autonomous`, `balanced`, `strict`) stored in `settings.db` across 6 trust gates (`read_only` vs `state_change` vs `destructive`) | Standing rule: code owns control; user sets permission, selection only narrows; deny always wins |
| **Setup & Verification** | `deploy/`, `preflight.py` (`--fast` / `--release`), `scripts/live_qa.py` (Playwright desktop + phone against real models) | `pytest` unit/integration + live markers | `./run.sh` + `local_setup.py` auto-probing ports `8000, 8006, 11434` + `scripts/check.py --live` across `.env.target.<name>` files + `.githooks/pre-commit` privacy scanner |

---

## 2. Kernel Execution, Control Flow & Turn Tracing

### How the three systems compare
1. **Control Ownership (`Agent-OS` P3 vs. `AutoReiv` ReAct/Graph)**
   - In **Agent-OS** (`agent_os/turn.py`, `agent_os/recipes.py`, `docs/research/product-journey.md`), **Code Owns Control**: the model never grades itself and never improvises multi-step infrastructure routines when code can walk the state machine. Every tool in `agent_os/recipes.py` defines three functions: `validate(arguments)` (pre-check), `run(arguments)` (execution), and `check(result)` (post-check on output structure). Furthermore, `run_past_chat_search` appends a deterministic stop signal (`answer_now(count)`) once hits are found or `search_max_per_turn` is reached, preventing model search loops.
   - In **Crucible** (`src/agent_os/kernel/companion_front_door.py`, `dispatcher.py`, `return_marshaller.py`), the front-door companion handles fast conversational turns while dispatching multi-step jobs to an isolated worker sandbox (`RecipeChamber`) that returns a schema-checked, bounded summary envelope ($\le 200$ tokens) so raw tool logs never pollute the main chat history.
   - In **AutoReiv** (`src/application/chat/`, `src/infrastructure/execution/`), background jobs and subagent delegations already isolate heavy work from the chat stream, and `CARD-696` exposed terminal failure reasons (`error_detail`) directly on failed job cards. However, AutoReiv tools currently rely primarily on input JSON Schema validation rather than deterministic post-execution output contracts (`check(result)`), and per-turn execution spans are spread across logs and database tables rather than a single inspectable turn trace artifact.

2. **Per-Turn Span Waterfall (`Agent-OS` `trace.py` & `Crucible` `ADR-0008`)**
   - **Agent-OS** (`agent_os/trace.py`) writes one self-contained, credential-scrubbed (`redact.py`) JSONL file per turn (`data/traces/<turn_id>.jsonl`) using OpenTelemetry span semantics (`trace_id`, `span_id`, `parent_span_id`, `start_time_unix_nano`, `duration_ms`, `status`, `attributes`) covering `turn`, `user_input`, `compaction`, `model_request`, `model_response`, `tool_call`, `tool_result`, and `final_answer`. Operators or agents can run `python -m agent_os traces` or `python -m agent_os trace <turn_id> [--full]` to render an instant indented latency waterfall, and optionally mirror spans to an OTLP collector via `AGENT_OS_OTLP_ENDPOINT` (`agent_os/otlp.py`).
   - **Crucible** (`ADR-0008`, `rca_stager.py`) complements raw traces with self-monitoring recipes (`system_health_audit`) and stages Root Cause Analysis (RCA) markdown proposals (`rca_[slug].md`) when recurring tool failures ($>20\%$) or latency anomalies occur, without ever self-modifying kernel code.

---

## 3. Capabilities: Skills, Recipes, Ingredients & Tools

### How the three systems compare
1. **Skill & Recipe Packaging**
   - **AutoReiv** (`ADR-0061`, `ADR-0062`, `CARD-687`..`CARD-693`) converged on a clean, unified model: every capability is an **Agora Skill folder** (`SKILL.md` with YAML frontmatter `name`, `description`, `tools:` + optional `scripts/` and `references/`) paired with callable **Tools**. `resolve_allowed_tools(agent)` in `src/application/agent_skills/allowed_tools.py` is the single code path deciding an agent's permitted tools, and `CARD-688` narrows active session skills per turn so the model sees at most 15 tools (`ADR-0054`).
   - **Crucible** evolved through three iterations (`ADR-0011` $\rightarrow$ `ADR-0013` $\rightarrow$ `ADR-0014` $\rightarrow$ `ADR-0015`). Notably, `ADR-0015` documents hard-won empirical findings from Crucible's earlier mistakes:
     - Keyword/regex triage (`ADR-0011`, `ADR-0013`) proved brittle under paraphrase and required code edits per domain.
     - Pure embedding similarity also failed as a standalone gate: in Crucible's 7-model benchmark (`ADR-0015` §4.4), chitchat cosine similarity (`0.75` max on `bge-small-en-v1.5`) overlapped valid recipe matches (`0.57` min), and embeddings confused `list` vs `read` vs `delete` on the same resource.
     - Crucible solved this by adding a **Capability Signature** (`verb` $\cdot$ `resource` $\cdot$ `scope` $\cdot$ `effect`) and requiring **contract examples** on synthesized tools that run automatically on synthesis, refactor, and nightly maintenance.
   - **Agent-OS** (`agent_os/recipes.py`, `recipes/look-up-past-chats/CONTEXT.md`, `docs/research/icm-folders-as-recipes.md`, `docs/research/tool-count-benchmark.md`) keeps recipes human-readable (`CONTEXT.md` with `When to use`, `Inputs`, `Process`, `Outputs`) and plans an empirical **Tool-Count Benchmark** (`5, 15, 30, 50` tools $\times$ `distinct` vs `similar` distractors $\times$ `one-per-function` vs `merged action parameter`) before adding complex retrieval machinery.

2. **Key Takeaway for AutoReiv**
   - AutoReiv's Agora `SKILL.md` folder format (`CARD-687`) and `resolve_allowed_tools(agent)` (`ADR-0061`) are significantly cleaner and less over-engineered than Crucible's 5-kind `ingredients.db` + ONNX embedding pipeline.
   - However, two specific ideas from Crucible `ADR-0014`/`ADR-0015` and Agent-OS `recipes.py` directly strengthen AutoReiv's existing tool/skill lifecycle without adding architectural bloat:
     1. **Executable Smoke Examples & Action Effect Tiers on Tools (`ADR-0015` §4.2–4.3)**: Tagging tools with an explicit `effect` (`read_only` | `state_change` | `destructive`) and a deterministic smoke test/example that runs during `create_user_tool` / `update_user_tool` (`CARD-695`, `CARD-697`).
     2. **Merged Action-Parameter Tools vs. Tool Sprawl (`Agent-OS` `tool-count-benchmark.md`)**: Grouping closely related CRUD operations under one cohesive tool or skill rather than proliferating near-duplicate tool names that degrade small/local model tool-calling accuracy.

---

## 4. State, Memory, Compaction & Hot/Cold Session Archiving

### How the three systems compare
1. **Deterministic Summary Verification during Compaction (`Agent-OS` `compaction.py`)**
   - Standard LLM conversation summarization suffers from silent fact drop: when a local model summarizes older turns, it frequently drops exact file paths, port numbers, dates, or snake_case identifiers, or accidentally hallucinates/continues the conversation instead of summarizing.
   - **Agent-OS** (`agent_os/compaction.py`) solves this with a deterministic code gate (`check_summary(summary, original)`):
     - It wraps the transcript in `<conversation>...</conversation>` with a strict `SUMMARIZER_ROLE` (`"You do not continue the conversation... Do not call tools"`).
     - It requires three structured headings: `Decisions`, `Open tasks`, and `Key facts`.
     - It extracts `KeyTokens` (`paths`, `numbers`/timestamps, and snake_case/file `names`) from the user's messages and any earlier summary ( deliberately ignoring verbose tool output via `fact_lines()` and `LONG_TOOL_LINE = 400`), normalizes Unicode dashes (`U+2010`–`U+2015`, `U+2212`) via `normalize_text()`, and verifies that **every required path, number, and identifier is preserved in the summary** and that `len(summary) < len(original)`.
     - If check 1 fails, it retries once; if attempt 2 fails, it leaves the original messages untouched and sets a turn backoff (`compaction_backoff_turns`) so the turn never blocks or corrupts history.
     - When accepted, the original rows are **never deleted or overwritten**; `archive_links` links them to the summary row.

2. **Hot/Cold Partitioning & Provenance-Tagged Recall (`Crucible` `ADR-0009` & `Agent-OS` `retention.py`)**
   - Both **Crucible** (`ADR-0009`) and **Agent-OS** (`agent_os/retention.py`, `agent_os/search.py`) separate **Hot Storage** (active recent turns) from **Cold Archive Storage** (`cold/chat.sqlite` + `cold/traces/`), verifying byte/snapshot integrity before pruning hot rows.
   - When searching past chats (`find_past_chats` in Agent-OS; `session_search_history` in Crucible), results carry explicit **provenance badges** (`recent` / `[Active Session]` vs `archived` / `[Cold Archive]`) and local-timezone dates, preventing the model from confusing a 6-month-old archived discussion with an active instruction.

---

## 5. Autonomy, Governance, Self-Authoring & Graduation

### How the three systems compare
1. **Granular Autonomy Matrix (`Crucible` `ADR-0015` §4.6 vs. `AutoReiv` `CARD-691`)**
   - In `CARD-691`, AutoReiv introduced `AUTOREIV_APPROVAL_MODE` (`strict` vs `hands_off`) so `AutoReiv` can create, test, and auto-enable custom tools and Agora skills end-to-end when `hands_off` is set.
   - **Crucible** (`ADR-0015` §4.6) refines this binary switch into a 3-mode runtime setting (`autonomous` / `balanced` / `strict`) crossed with tool `effect` (`read_only`, `state_change`, `destructive`):
     - In `balanced` mode (the recommended daily driver for a local companion), **mounting or promoting a `read_only` tool/skill is automatic**, whereas mounting or executing `state_change` or `destructive` capabilities still gates on user approval.
     - Crucible also persists this mode in SQLite settings (`settings.db` > `.env` > default) so the operator can toggle it live in the UI or chat without restarting the server.

2. **Self-Healing Tool Primitives (`Crucible` `ADR-0014` §3.2)**
   - Crucible's "Self-Healing Litmus Test" (`ADR-0014`) requires that the agent not only create tools, but also **inspect**, **refactor** (with pre-flight dry-run verification), and **retire** existing user tools (`tool_inspect`, `tool_refactor`, `tool_retire`).
   - AutoReiv just completed `update_user_tool` and `update_skill` in `CARD-695` and hardened end-to-end self-authoring in `CARD-697`, putting AutoReiv ahead of both Crucible and Agent-OS in real browser-verified self-building. Adding a `retire_user_tool` / `delete_user_tool` + `delete_user_skill` lifecycle action (or exposing `ApprovalMode` in Settings UI) is the natural next step.

---

## 6. Operator Surface, Zero-Friction Setup & Verification Loops

### How the three systems compare
1. **Local Model Port Probing (`Agent-OS` `local_setup.py`)**
   - **Agent-OS** (`agent_os/local_setup.py`) provides a zero-friction first-run experience: `./run.sh` / `python -m agent_os setup` probes `127.0.0.1` across common local inference ports (`8000`, `8006`, `11434`, or `AGENT_OS_PROBE_PORTS`), queries `/v1/models`, auto-detects the machine's IANA timezone (`/etc/timezone`, `/etc/localtime`), and populates `.env` if the configured model isn't currently served.
   - AutoReiv already has a Models studio and provider health checks, but adding a one-click or startup local-port auto-discovery probe (`8000, 8006, 11434`) when no active endpoint responds would eliminate manual URL entry when switching between vLLM and Ollama.

2. **Verification Loops (`AutoReiv` `live_qa.py` + `preflight.py` vs. `Agent-OS` `check.py` + `.githooks`)**
   - **AutoReiv** leads on end-to-end UI and agent verification: `scripts/live_qa.py` runs real Playwright journeys across both desktop (`1280x800`) and phone (`390x844`) viewports against an isolated throwaway server on `:8770`, and `preflight.py --fast` enforces architecture guards in ~25 seconds.
   - **Agent-OS** adds two lightweight developer-hygiene mechanisms worth noting:
     - `.githooks/pre-commit`: a fast stdlib regex check that blocks commits containing private LAN IPs, personal home-folder paths, or leaked API keys.
     - Multi-target live matrix (`.env.target.<name>`): running the same structural agent check across multiple local model targets side-by-side and writing a compact `.checks/summary.md`.

---

## 7. Prioritized Recommendations for AutoReiv (Adopt / Adapt / Skip)

### Tier 1 — Adopt (High Leverage, Low Complexity, Fits AutoReiv's Architecture)

1. **[Adopt — P1] Token-Verified Context Compaction with Non-Destructive `archive_links` (from `Agent-OS` `compaction.py`)**
   - **Why**: Local models frequently drop file paths, numbers, or identifiers during chat summarization. Agent-OS's deterministic post-check (`check_summary`: 3 required sections `Decisions` / `Open tasks` / `Key facts` + regex extraction of user paths/numbers/identifiers + Unicode dash folding + 1 retry + backoff + keeping original rows linked via `archive_links`) guarantees compaction never silently loses critical facts.
   - **Where in AutoReiv**: `src/application/chat/` session compaction service and `src/infrastructure/storage/`.

2. **[Adopt — P1] Per-Turn Structured Span Waterfall & Trace Inspector (from `Agent-OS` `trace.py` + `Crucible` `ADR-0008`)**
   - **Why**: When a multi-step chat turn or background job is slow or fails, operators shouldn't have to correlate multiple log lines. Writing a per-turn/per-job span tree (`user_input` $\rightarrow$ `compaction` $\rightarrow$ `model_request` $\rightarrow$ `tool_call` $\rightarrow$ `tool_result` $\rightarrow$ `final_answer`) with credential scrubbing and exposing a clean latency waterfall in the Job/Turn drawer (and CLI) gives instant observability.
   - **Where in AutoReiv**: `src/infrastructure/telemetry/` + Chat job/turn detail drawer (`src/web/static/js/`).

3. **[Adopt — P2] Runtime `ApprovalMode` (`strict` / `balanced` / `hands_off`) in Settings UI + `read_only` Tool Effect Tier (from `Crucible` `ADR-0015` §4.6)**
   - **Why**: `CARD-691` added `AUTOREIV_APPROVAL_MODE` as an environment variable (`strict` vs `hands_off`). Surfacing this in the Settings Studio (`settings.db` / runtime config) and adding a `balanced` middle tier—where `read_only` tools/skills auto-mount after passing smoke validation while `state_change`/`destructive` tools still require approval—gives Jacob hands-free ergonomics without sacrificing safety.
   - **Where in AutoReiv**: `src/application/agent_skills/`, `src/web/routes/settings.py`, and Settings Studio UI.

### Tier 2 — Adapt (Valuable Concepts to Tailor to AutoReiv)

4. **[Adapt — P2] Provenance-Badged Cross-Session & Hot/Cold History Search Tool (from `Crucible` `ADR-0009` & `Agent-OS` `recipes.py` / `retention.py`)**
   - **Why**: Giving `AutoReiv` a dedicated platform tool (`search_past_chats`) that queries FTS5 across active and archived sessions, enforces a per-turn call cap (`search_max_per_turn = 2`) with a deterministic `"Answer now from what you have"` trailer, and labels hits `[Recent Session]` vs `[Archived Session]` with local dates prevents search loops and temporal confusion.
   - **Where in AutoReiv**: `src/application/tools/` platform tools (`REQUIRED_PLATFORM_TOOLS`) + SQLite FTS5 index over chat messages.

5. **[Adapt — P3] Local Model Port Auto-Probe in Models Studio & Startup (from `Agent-OS` `local_setup.py`)**
   - **Why**: Probing `127.0.0.1` ports `8000, 8006, 11434` (`/v1/models`) and surfacing discovered local servers as one-click cards in Models Studio removes manual URL/model-ID typing.
   - **Where in AutoReiv**: `src/application/models/` and Models Studio (`src/web/static/js/`).

6. **[Adapt — P3] Staged RCA / Improvement Proposals on Recurring Tool Failures (from `Crucible` `ADR-0008`)**
   - **Why**: When a user tool or routine fails repeatedly, staging an actionable RCA note (with trace IDs, error detail from `CARD-696`, and a one-click "Ask AutoReiv to fix with `update_user_tool`" action) closes the self-healing loop safely.

### Tier 3 — Skip (Do Not Adopt in AutoReiv)

7. **[Skip] Crucible's 5-Kind `ingredients.db` Schema & In-Process ONNX `bge-small` Embedding Router (`Crucible` `ADR-0015` §4.2, §4.4)**
   - **Why**: AutoReiv's Agora `SKILL.md` folder architecture (`ADR-0061`, `ADR-0062`, `CARD-687`..`CARD-693`) and `resolve_allowed_tools(agent)` single lever are much simpler, human-editable on disk, and already verified in live QA. Adding a 210 MB RSS ONNX embedding model and a 5-table relational ingredient graph would re-introduce the dual-system complexity retired in M27–M28.
8. **[Skip] Replacing the Web Studio UI with a Pure Terminal UI (`Agent-OS` P2 extreme)**
   - **Why**: While "Chat as the primary control surface" (`CARD-691`, `CARD-697`) is already a core AutoReiv strength, AutoReiv's responsive Web Studios (Capabilities tree, Wiki, Tutor, Routines) provide high-bandwidth visual inspection and control on both desktop and phone that a terminal-only UI cannot match.

---

## 8. Decision Options for Next Milestone

At check-in, Jacob can choose how to sequence the **Tier 1 (Adopt)** and **Tier 2 (Adapt)** recommendations into the roadmap:

- **Option 1 (Recommended — Adopt Tier 1 as the next 3 cards)**:
  1. **Token-verified context compaction & `archive_links`** (adapted from `Agent-OS` `compaction.py`).
  2. **Per-turn / per-job span waterfall trace inspector** in Chat & Job drawer (adapted from `Agent-OS` `trace.py`).
  3. **Live `ApprovalMode` (`strict` / `balanced` / `hands_off`) in Settings UI** with `read_only` vs `state_change` tool effect gating (adapted from `Crucible` `ADR-0015` §4.6).
- **Option 2 (Adopt Tier 1 + Tier 2 batch)**:
  - Queue all 6 **Adopt + Adapt** items above (adding provenance-badged `search_past_chats`, local model port auto-probing on `8000/8006/11434`, and staged RCA self-healing prompts).
- **Option 3 (Reference only for now)**:
  - Keep `docs/architecture-comparison-crucible-agent-os.md` as a reference document and pick individual items later during milestone triage.
