# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## Unreleased

- User data directory (`AutoReiv.Data` - CARD-102):
  - `DataDirResolver` resolves `AUTOREIV_DATA_DIR` env > persisted `data_dir` setting > platform default (`%LOCALAPPDATA%\AutoReiv` on Windows, `~/.autoreiv` on POSIX, `/data` in Docker) (`[REQ-DATA-001]`, `[REQ-DATA-002]`).
  - Database, wiki, and skills paths derive from the data dir unless `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH` are explicit (`[REQ-DATA-003]`).
  - First boot copy-migrates live `./data/autoreiv.db` and `./data/wiki` into an empty dest. Copy, not move. Does not overwrite dest. Does not wipe source (`[REQ-DATA-004]`).
  - Wired in `create_app`, CLI `--data-dir`, `.env.example`, Docker one volume at `/data` (`[REQ-DATA-005]`, `[REQ-DATA-006]`).

- Control-plane data dir (`docs/specs/control-plane-data-dir/` - CARD-102-105): spec and Slice B cards opened. User data dir outside the checkout, backup/restore, user SKILL.md packs via DynamicSkillLoader, Skills Studio. No feature code. No push.

- propose_followup draft jobs (`AutoReiv.Orchestration`, `AutoReiv.Skills` - CARD-101):
  - `propose_followup` writes a `proposals` row kind `followup_job` status `draft` with `requested_by_job_id`, plus a queued Job (`template_id=followup_job`) and a HITL `pending_approvals` park (`[REQ-ORCH-043]`).
  - Creating the draft does not start a phase and does not call `stream_turn` / the kernel. There is no `set_goal` tool.
  - Approve marks the proposal `approved` and leaves the Job `queued`. It does **not** auto `stream_turn`. Reject marks `rejected` and cancels the job.
  - Tool is mounted on OrchestrationSkill next to `handoff_to_agent`. Allowlisted on Conductor / Assistant / AutoReiv, not Coding or Review.

- Chat Job/Phase status strip (`AutoReiv.Chat` - CARD-100):
  - Chat shows job status, current phase name, assigned agent, and react_state (THINKING / CALLING_TOOLS / PARKED / DONE / FAILED) from SSE (`[REQ-ORCH-042]`).
  - Goal badge is "Multi-phase job" (not Plan Graph). PARKED and FAILED are named in the strip.

- Bind chat Goal and Verify to persisted Job/Phase (`AutoReiv.Orchestration`, `AutoReiv.Chat`, `AutoReiv.Kernel` - CARD-099):
  - Default chat creates one Job + one Phase and runs `stream_turn` (`[REQ-ORCH-035]`).
  - Goal mode uses a no-tool `gateway.complete` planner (tools disabled; not `run_turn`), persists linear Job+Phases, and waits for HITL `goal_plan_review` before per-phase `stream_turn` (`[REQ-ORCH-039]`, `[REQ-ORCH-040]`).
  - Verify is a named checker gate; a missing checker is an honest skip and does not claim `verification_passed` (`[REQ-ORCH-041]`).
  - SSE emits `job_created` / `phase_start` / `phase_complete` plus existing `react_state` job/phase ids.

- Packet handoff via stream_turn (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-098):
  - Child handoff requires a `HandoffPacket` (goal, facts, constraints, done_when, budget). The child user message is the packet only; parent transcript is not copied (`[REQ-ORCH-036]`).
  - Child runs `stream_turn` on a new empty session with the child's full context window. No `run_turn` / nested `complete()`, no 32k CARD-094 cap on this path (`[REQ-ORCH-037]`).
  - Global Ollama generation semaphore default 1 (setting `max_concurrent_generations` range 1-3). Extra generations QUEUE. A handoff batch larger than the cap errors and is not silent-truncated (`[REQ-ORCH-038]`).

- Named ReAct States (`AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-097):
  - AgentKernel overlays THINKING|CALLING_TOOLS|PARKED|DONE|FAILED on the existing loop and persists `phase.react_state` when phase_id is in scope (`[REQ-KERNEL-001]`).
  - Chat SSE emits `react_state` with react_state, turn_idx, job_id, phase_id, assigned_agent_id (`[REQ-KERNEL-002]`). No LangGraph. No Chat badge (CARD-100).

- Job/Phase records + orchestrator (AutoReiv.Orchestration - CARD-096): SQLite jobs/phases, JobRepositoryMixin, JobPhaseOrchestrator linear next-or-finish. No LLM. No LangGraph.

- Control-plane Job/Phase (`docs/specs/control-plane-job-phase/` - CARD-096-101): spec and Slice A cards opened. CARD-014 parked (superseded by Job/Phase; DAG idea not deleted). No feature code. No push.

- Card board hygiene: parked CARD-023 through CARD-028 (nothing in flight). Closed CARD-046 (shipped as 063) and CARD-058 (already in CHANGELOG). Real backlog stays Ready. No push.


- Nested Write Budget (`AutoReiv.Orchestration`, `AutoReiv.SDLC` - CARD-095):
  - Nested `max_tokens` is 8192 and Ollama read timeout is 600s so CARD-001 can actually write `react-loop.ps1` (`[REQ-ORCH-030]`).
  - `git_status` / `git_commit` on a non-repo return `skip_commit`. Coding writes the deliverable first (`[REQ-SDLC-073]`).


- Nested Complete Context Cap (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-094):
  - `run_turn` caps `num_ctx` at 32768 and `max_tokens` at 1024. Nested `complete()` sends `think=false` (`[REQ-ORCH-028]`, `[REQ-ORCH-029]`).
  - Conductor handoff passes card id + spec slug. Coding reads the spec; it does not paste bodies.


- Nested Complete Uses Stream (`AutoReiv.Gateway`, `AutoReiv.Orchestration` - CARD-092):
  - Ollama `complete()` consumes `stream=true` so Coding handoff shares Chat's HTTP shape (`[REQ-ORCH-026]`).
  - Usage comes from the done chunk. Timeout/connect/404 labels unchanged (`[REQ-ORCH-027]`).

- Persist Builtin Agent Purpose (`AutoReiv.Forge`, `AutoReiv.Agents` - CARD-093):
  - `AgentCustomization.purpose` is saved on builtin Forge updates and applied on GET (`[REQ-FORGE-020]`).
  - Invalid purpose strings are ignored (`[REQ-FORGE-021]`).


- Close Parent LLM Stream Before Child Handoff (`AutoReiv.Orchestration`, `AutoReiv.Gateway` - CARD-091):
  - `stream_turn` acloses the parent LLM stream before tools so Coding `complete()` is not nested inside the Conductor HTTP request (`[REQ-ORCH-023]`).
  - `gateway.stream` acloses inner `provider.stream`. Ollama POSTs relative `/api/chat`; pool timeout is 30s (`[REQ-ORCH-024]`).
  - `TimeoutException` is `Ollama timed out at ...`, not Failed to connect. Connect/timeout still HandoffResult failed (`[REQ-ORCH-025]`).

- Handoff Child Turn Budget (`AutoReiv.Orchestration` - CARD-090):
  - Child handoff `max_turns` defaults to 10 and is `min(max(envelope, profile, 10), 15)` so Coding is not silently capped at 5 (`[REQ-ORCH-020]`).
  - Provider connection failures (`Failed to connect`, `candidate providers failed`) map to HandoffResult status `failed` / success False, not completed (`[REQ-ORCH-021]`).
  - Ollama connect timeout is 30s; nested `complete()` uses its own httpx client so it is not starved by the parent stream (`[REQ-ORCH-022]`).

- YAML Card Frontmatter (`AutoReiv.SDLC` - CARD-089):
  - `parse_card_frontmatter` reads YAML `---` KEY: VALUE `---` plus blockquote `> **Key**: value`. Blockquote wins on conflict; YAML fills missing keys (`[REQ-SDLC-070]`).
  - `spec_reference` aliases Spec Reference / spec_reference / spec; `status` aliases Status / status (`[REQ-SDLC-071]`).
  - YAML-origin cards keep YAML on `set_card_status`. Discuss -> Ready works when the spec dir exists (`[REQ-SDLC-072]`).

- Spec-Driven SDLC Team (`AutoReiv.SDLC` - CARD-080-089): Conductor / Coding / Review loop on project-scoped cards and specs. Jail, Projects studio, SDD scaffold, conventional git, GitHub issue sync. Hold all pushes.

- Cards As GitHub Issues (`AutoReiv.SDLC` - CARD-088):
  - `sync_card_issue` maps card status and type labels and uses `gh` when present (`[REQ-SDLC-040]`, `[REQ-SDLC-041]`).
  - Missing `gh` is a clear error. No tokens. No GitHub MCP. HITL on create/update (`[REQ-SDLC-042]`).

- Git Conventional Commits (`AutoReiv.SDLC`, `AutoReiv.Agents` - CARD-087):
  - `git_status`, `git_diff`, `git_branch`, `git_commit` are jailed to `project_root`. Conventional subjects only (`[REQ-SDLC-060]`).
  - `git_commit` parks on HITL. Coding allowlist stays at 12. No push (`[REQ-SDLC-061]`).

- SDD Project Scaffold (`AutoReiv.SDLC` - CARD-086):
  - `create_project` copies `templates/sdlc-project/` (AGENTS.md, specs, cards, CHANGELOG, VERSION, CONTRIBUTING, tests, README) (`[REQ-SDLC-050]`).
  - Tool is registered and HITL-parked. Slug cannot escape `projects_root` (`[REQ-SDLC-053]`).

- Projects Studio (`AutoReiv.SDLC`, `AutoReiv.Web` - CARD-085):
  - `projects_root` setting plus GET/POST/DELETE `/api/projects` jailed under that root (`[REQ-SDLC-050]`, `[REQ-SDLC-051]`).
  - Projects Studio is a sidebar tab, not wiki. Selected project is the default card/file root (`[REQ-SDLC-052]`).

- SDLC Bounce Back (`AutoReiv.SDLC`, `AutoReiv.Agents` - CARD-084):
  - Bounce-back is the CARD-080 state machine plus `handoff_to_agent`. No second engine (`[REQ-SDLC-006]`).
  - Coding may `set_card_status` In Progress -> In Review only and is granted card/file tools under 12 (`[REQ-SDLC-033]`).

- Review Builtin (`AutoReiv.Agents` - CARD-083):
  - Builtin Review (`id=review`) has a 9-tool allowlist. Writes and `execute_code` are denied (`[REQ-SDLC-031]`).
  - Aliases qa / tester / review. Review can set Returned or Done from In Review (`[REQ-SDLC-035]`).

- Conductor Builtin (`AutoReiv.Agents` - CARD-082):
  - Builtin Conductor (`id=conductor`) has an 11-tool allowlist. No `execute_code`, `cli_exec`, or `write_project_file` (`[REQ-SDLC-030]`).
  - Lookup aliases product / plan / scrum / conductor. Chat and Forge list it without a Forge save (`[REQ-SDLC-034]`).

- Project File Tools (`AutoReiv.SDLC` - CARD-081):
  - `list_project_dir`, `read_project_file`, `write_project_file` are jailed under `project_root` (`[REQ-SDLC-021]`, `[REQ-SDLC-022]`).
  - Writes park on existing HITL. Grants wait for Conductor / Review / Coding cards (`[REQ-SDLC-023]`).

- Card Spec Steering Tools (`AutoReiv.SDLC` - CARD-080):
  - Tools `list_cards`, `read_card`, `write_card`, `set_card_status`, `read_spec`, `write_spec`, `read_steering` operate on `project_root` (default AutoReiv checkout) (`[REQ-SDLC-012]`, `[REQ-SDLC-013]`).
  - `set_card_status` enforces Discuss | Ready | In Progress | In Review | Returned | Done. Ready needs a spec. Returned increments rounds; max rounds deny and tell the caller to ask the operator (`[REQ-SDLC-010]`, `[REQ-SDLC-011]`).
  - Writes and status changes park on existing HITL (`[REQ-SDLC-014]`, `[REQ-SDLC-020]`).

- Coding Agent Execute Code (`AutoReiv.Agents`, `AutoReiv.Kernel` - CARD-079):
  - Builtin Coding agent is in the roster with a tight allowlist. `execute_code` is granted only on Coding (`[REQ-AGENTS-010]`).
  - Bootstrap registers the sandbox skill so `execute_code` is in the Forge catalog; Assistant is allowlist-denied (`[REQ-AGENTS-011]`).
  - Chat, Forge, and `lookup_agents` list Coding without a Forge save. SQLite overrides still win (`[REQ-AGENTS-012]`).

- Routine Resume From Chat (`AutoReiv.Routines`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-076):
  - Routine parks store `agent_id` and `routine_id` so Chat can list them (`[REQ-HITL-041]`).
  - Chat loads pending approvals for the open agent and shows the existing Approve/Reject card (`[REQ-HITL-042]`).
  - Approve/Reject on a routine park resumes that session with `run_turn(..., resume=True)` and no extra USER (`[REQ-HITL-043]`).

- Forge Allowlist Warning (`AutoReiv.Web` - CARD-078):
  - Forge shows an amber warning when 12 or more tools are checked; save is not blocked (`[REQ-FORGE-007]`, `[REQ-FORGE-008]`).

- Card status hygiene: normalize `.github/cards` labels to Done / Ready / In Progress.

- Remember Last Auto-run (`AutoReiv.Web` - CARD-077):
  - Chat Auto-run toggle is remembered in localStorage; missing memory fail-closes to ask (`[REQ-HITL-039]`, `[REQ-HITL-040]`).

- Goal Mode Review Gate (`AutoReiv.Planning`, `AutoReiv.Web` - CARD-075):
  - Goal Mode parks after formulate so the operator can Approve or Reject the plan (`[REQ-GOAL-020]`, `[REQ-GOAL-021]`).
  - Approve runs the existing step executor; Reject ends cleanly. Send a message to revise (`[REQ-GOAL-022]`).

- Nested Child-Session HITL Resume (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-074):
  - Nested Approve/Reject persist the TOOL on the child session and resume child ReAct with no new USER message (`[REQ-HITL-036]`).
  - Child completion or a second park is written onto the parent as a handoff TOOL (`[REQ-HITL-037]`).
  - Parent resume replays a nested park and stops, or continues after the child result (`[REQ-HITL-038]`).

- Resume After HITL Approve (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-073):
  - After Approve or Reject, Chat starts a continue stream with no new USER message (`[REQ-HITL-033]`).
  - `stream_turn` resume loads existing history and continues ReAct (`[REQ-HITL-034]`). Failed decide does not resume (`[REQ-HITL-035]`).

- Stop Stream After HITL Park (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-072):
  - `stream_turn` yields TURN_END and returns after a gated or nested park so the model cannot keep talking (`[REQ-HITL-031]`).
  - Parked handoffs emit `HANDOFF_COMPLETE` with `status=approval_required`; Chat shows Waiting for approval / Parked (`[REQ-HITL-032]`).

- Agent Chat History Retention (`AutoReiv.Agents`, `AutoReiv.Memory` - CARD-047):
  - Per-agent `history_retention_days` defaults to 30. `0` means never (`[REQ-RET-001]`).
  - Stale chat sessions and messages are pruned on startup and when Chat lists sessions (`[REQ-RET-002]`, `[REQ-RET-004]`).
  - Wiki, facts, and routines are not touched (`[REQ-RET-003]`).

- Session And Routine Approval Mode (`AutoReiv.Safety`, `AutoReiv.Web` - CARD-071):
  - Chat Auto-run toggle sends `approval_mode=run`; default is ask (`[REQ-HITL-027]`).
  - Handoff inherits the parent turn policy (`[REQ-HITL-028]`).
  - Routines store `approval_mode` on the job, default ask (`[REQ-HITL-029]`).
  - Run mode still hard-denies dangerous `cli_exec` (`[REQ-HITL-030]`).

- Keep HITL Approve Output On Screen (`AutoReiv.Web`, `AutoReiv.Safety` - CARD-070):
  - Stream-end history reload no longer wipes a visible HITL card (`[REQ-HITL-025]`).
  - Approve/Reject persist the tool output on the chat session (`[REQ-HITL-026]`).

- Bubble Child HITL Parks To Parent Chat (`AutoReiv.Orchestration`, `AutoReiv.Safety` - CARD-069):
  - A specialist that parks a tool during handoff now surfaces `approval_required` on the parent stream (`[REQ-HITL-023]`, `[REQ-HITL-024]`).
  - Chat Approve/Reject cards use the child tool name and arguments.

- Chat HITL Approve / Reject Buttons (`AutoReiv.Web`, `AutoReiv.Safety` - CARD-068):
  - Chat stream shows a HITL card with tool name, arguments, Approve, and Reject (`[REQ-HITL-020]`).
  - Buttons call `POST /api/approvals/{id}/decision`; the card shows the result (`[REQ-HITL-021]`, `[REQ-HITL-022]`).

- Allowlist-Only Tool Mount (`AutoReiv.Kernel`, `AutoReiv.Agents` - CARD-067):
  - Chat turns mount the full RBAC allowlist; BM25 no longer drops granted tools (`[REQ-TOOLS-010]`).
  - Assistant pins `lookup_agents` next to `handoff_to_agent` (`[REQ-TOOLS-011]`).
  - `list_available_skills_and_tools` is no longer on builtin chat allowlists; Forge still lists the catalog (`[REQ-TOOLS-012]`).

- Unify Agent Handoff To One Public Tool (`AutoReiv.Orchestration`, `AutoReiv.Kernel` - CARD-066):
  - Chat now exposes only `handoff_to_agent`; `delegate_task` is no longer registered (`[REQ-ORCH-010]`).
  - App startup injects the live kernel into `HandoffIsolationEngine` (`[REQ-ORCH-011]`).
  - Caller agent id and session come from the in-flight turn so child sessions follow the real chat (`[REQ-ORCH-012]`).

- Keep Reflexion Critiques Off Transcript (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-065):
  - Self-verify retries no longer persist `CRITIQUE ON PREVIOUS OUTPUT` as USER messages (`[REQ-VERIFY-014]`, `[REQ-VERIFY-015]`).
  - Chat SSE emits `reflexion_attempt` per try and `reflexion_critique` on each failed check (`[REQ-VERIFY-016]`).

- Honest Reflexion Verification (`AutoReiv.Kernel`, `AutoReiv.Web` - CARD-064):
  - Missing verifier/critic is now `skipped` with `verification_passed=false` instead of a fake pass (`[REQ-VERIFY-010]`).
  - Chat `self_verify` runs a builtin JSON critic (`is_valid` / `discrepancies`) and fails closed on empty output or unparseable critic JSON (`[REQ-VERIFY-011]`, `[REQ-VERIFY-012]`).
  - SSE `reflexion_verified.passed` matches the engine; Chat Studio shows a failed badge when verification does not pass (`[REQ-VERIFY-013]`).

- Wire HITL Approval Into Kernel Tool Loop (`AutoReiv.Kernel`, `AutoReiv.Safety`, `AutoReiv.Web` - CARD-063):
  - `AgentKernel` parks high-risk tools (`cli_exec`, wiki writes, `save_agent_specification`, `execute_code`) in `pending_approvals` instead of executing them (`[REQ-HITL-010]`, `[REQ-HITL-011]`).
  - `DangerousCommandFilter` hard-denies prohibited `cli_exec` commands without parking (`[REQ-HITL-012]`).
  - Chat stream emits `approval_required`; `POST /api/approvals/{id}/decision` with APPROVED runs the parked tool (`[REQ-HITL-013]`).


- Settings-Owned Model Context Window Overrides (`AutoReiv.Kernel`, `AutoReiv.Settings`, `AutoReiv.Gateway` - CARD-062):
  - Stopped treating `qwen3.8:latest` as an 8k model; name table now maps `qwen3.8` / `qwen35` and explicit size tags (`65k`, `256k`, `262k`) (`[REQ-CTX-001]`).
  - Added `default_context_window` and `model_context_windows` on the purpose matrix, editable in Settings Studio and saved via `POST /api/settings/matrix` (`[REQ-CTX-002]`, `[REQ-CTX-003]`).
  - Kernel compaction and Ollama `num_ctx` use the Settings override first, then the name table (`[REQ-CTX-004]`).

- Host OS-Aware Tool Guidance & System Info Description Alignment (`AutoReiv.Skills`, `AutoReiv.Agents` - CARD-061):
  - Updated `system_info` and `cli_exec` tool schema descriptions to advertise host IP capabilities and enforce OS-appropriate command syntax (`[REQ-OS-AWARE-001]`).
  - Enriched `AUTOREIV_PROFILE.system_prompt` with host OS awareness (Windows vs Linux) and directed the model to use `system_info` first for telemetry and platform-specific CLI commands (`[REQ-OS-AWARE-002]`).
  - **Fixed** `cli_exec` and `SandboxedSubprocessWorker` subprocess execution on Windows: uvicorn uses `SelectorEventLoop` which throws `NotImplementedError` on `asyncio.create_subprocess_shell/exec`. Replaced with `subprocess.run` dispatched via `loop.run_in_executor` (thread pool) for cross-platform compatibility.

- Host IP Telemetry in System Info & AutoReiv CLI Exec Pinning (`AutoReiv.Skills`, `AutoReiv.Agents` - CARD-060):
  - Enriched `SysadminSkill.get_system_info()` with `hostname`, `primary_ip`, and `ip_addresses` telemetry using resilient cross-platform UDP and DNS socket probes (`[REQ-SYSINFO-001]`, `[REQ-SYSINFO-003]`).
  - Pinned `cli_exec` in `AUTOREIV_PROFILE.pinned_tool_names` ensuring safe shell command execution is unconditionally delivered in active tool sets on every turn (`[REQ-SYSINFO-002]`).

- Mobile Stream Resiliency, Background Task Persistence & Goal Deliverable Markdown Synthesis (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Planning` - CARD-059):
  - Decoupled FastAPI `/api/chat/stream` SSE generator from underlying turn execution using shielded background worker tasks and in-memory async queues, guaranteeing database persistence even if mobile screen locks or tabs disconnect mid-stream (`[REQ-MOB-STREAM-001]`).
  - Implemented mobile tab visibility (`document.visibilitychange`) and window focus synchronization in Chat Studio to automatically re-fetch and restore completed messages upon returning to the app (`[REQ-MOB-STREAM-002]`).
  - Added strict Markdown output instructions and negative constraints against raw JSON dicts in Goal Mode synthesis prompts (`[REQ-MOB-STREAM-003]`).
  - Implemented graceful `format_json_deliverable_to_markdown` fallback formatter in both Python backend and JavaScript frontend to format structured deliverables into clean Markdown sections (`[REQ-MOB-STREAM-004]`).

- Visual Goal Mode & Reflexion Streaming UI (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Planning` - CARD-058):
  - Added `goal_mode` and `self_verify` boolean parameters to `/api/chat/stream` (`[REQ-CHAT-010]`).
  - Implemented SSE emission for multi-step goal execution (`plan_formulated`, `step_start`, `step_complete`) and self-verification (`reflexion_attempt`, `reflexion_critique`, `reflexion_verified`) (`[REQ-CHAT-011]`, `[REQ-CHAT-012]`).
  - Added interactive Milestone DAG progress card and real-time Reflexion verification badges inside Chat Studio message bubbles (`[REQ-CHAT-013]`).
  - Supported dual-mode execution where decomposed goal milestones run with iterative self-verification (`[REQ-CHAT-014]`).
  - Isolated plan formulation and step prompts from chat thread history (`save_to_history=False`) to prevent raw JSON and system prompts in chat bubbles.
  - Enhanced Gateway and Agent Kernel model cascade to correctly resolve configured default models (e.g. `qwen3.8:latest`) and increased Ollama read timeout to 180s for local reasoning models.
- Weekly Notes Rollover Routine & Markdown Task Skill (`AutoReiv.Skills`, `AutoReiv.Routines`, `AutoReiv.Web` - CARD-057):
  - Seeded default Obsidian-compatible weekly notes template in `data/wiki/03_Resources/templates/weekly_notes.md` with dynamic Monday–Sunday date interpolation (`[REQ-WNOTE-001]`).
  - Implemented `WeeklyNotesSkill` (`src/application/skills/weekly_notes_skill.py`) with conversational tools for logging daily progress, checking off tasks with `✅ YYYY-MM-DD`, and viewing weekly summaries (`[REQ-WNOTE-002]`).
  - Built automated task carry-over engine rolling over unfinished tasks from previous weeks into `### 🔄 Carry-Over` (`[REQ-WNOTE-003]`).
  - Added built-in autonomous routine `weekly_note_rollover` (`0 0 * * 1` Monday midnight) bound to `assistant` (`[REQ-WNOTE-004]`).
- Skill Pack Taxonomy Realignment & AutoReiv Dedicated Diagnostics (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-056):
  - Structured skill pack manifests into a 3-tier functional taxonomy: **User Knowledge & Productivity**, **System Operations & Platform**, and **Agent Cognition & Runtime** (`[REQ-TAX-001]`).
  - Branded internal diagnostics as `"AutoReiv Core Platform SRE & Diagnostics"` with dedicated core indicators and renamed self-reflection tools to `"Agent Logic Verification (Critic)"` (`[REQ-TAX-002]`).
  - Pruned redundant `yaml_frontmatter_parse` micro-tool from the tool registry in favor of `wiki_note_read`'s native metadata extraction (`[REQ-TAX-003]`).
  - Updated Agent Forge Studio to render skill packs grouped into 3 distinct visual sections with tier headers, subtitles, and dedicated badges (`[REQ-TAX-004]`).
- Session Artifact Store & Context-Isolated Batch Worker Skill (`AutoReiv.Memory`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-055):
  - Implemented SQLite `session_artifacts` schema with `ON DELETE CASCADE` session bound foreign keys, indexed 7-day TTL timestamps, and manual artifact pinning (`[REQ-ART-001]`, `[REQ-ART-002]`).
  - Built `BatchWorkerSkill` map-reduce pipeline partitioning massive target paths across parallel in-memory subagents and saving structured reports to `session_artifacts` (`[REQ-ART-003]`).
  - Added REST API endpoints (`/api/sessions/{id}/artifacts`, `/api/artifacts/{id}`, `/api/artifacts/{id}/promote`, `/api/artifacts/{id}/pin`) (`[REQ-ART-004]`).
  - Added Chat Studio interactive artifact cards in message bubbles and slide-over `#artifactModal` viewer with 1-click **"Promote to Wiki Vault"** capability (`[REQ-ART-005]`).
- Agent Forge Studio Mobile Responsive Toolbar, Header Cleanup & Default Collapsed Skills (`AutoReiv.Web` - CARD-054):
  - Removed obsolete `"RPG Character Sheet"` badge text from the Agent Forge Studio header (`[REQ-MOB-001]`).
  - Refactored the Agent Forge top toolbar into a mobile-first responsive flex container allowing dropdown and action buttons to wrap naturally on viewports $\le 480\text{px}$ (`[REQ-MOB-002]`).
  - Set skill pack tool item grids in Agent Forge to be collapsed by default upon page navigation for a compact overview (`[REQ-MOB-003]`).
- Agent Forge Studio Layout Refactor & Legacy Co-Pilot Pruning (`AutoReiv.Web` - CARD-053):
  - Removed obsolete "System Architect Co-Pilot" chat sidebar, starter prompt chips, and prompt input form from Agent Forge Studio (`[REQ-PRUNE-001]`).
  - Expanded RPG Character Sheet workspace into a clean, spacious full-width container (`max-w-6xl mx-auto`) with responsive single and multi-column grid cards (`[REQ-PRUNE-002]`).
  - Pruned unused Co-Pilot JS state, streaming handlers, and legacy `system-agent` stream calls from `src/web/static/modules/studios/forge.js` (`[REQ-PRUNE-003]`).
- MCP Server Environment Variables, Live Tool Discovery Preview & Agent Forge Pack Binding (`AutoReiv.MCP`, `AutoReiv.Web`, `AutoReiv.Skills` - CARD-052):
  - Enabled per-server secure key-value environment variables injection into MCP stdio subprocesses (`[REQ-MCP-007]`).
  - Added transient diagnostic handshake probe endpoint `POST /api/settings/mcp/test` measuring connection latency and advertising tool schemas without persistence (`[REQ-MCP-008]`).
  - Upgraded Settings Studio MCP panel with dynamic key-value environment editor, secret value masking, and live tool discovery badge preview (`[REQ-MCP-009]`).
  - Integrated dynamic MCP Server skill pack clustering and master checkboxes into Agent Forge Studio (`[REQ-MCP-010]`).
- Model Context Protocol (MCP) Standard Client Adapter & 3-Tier Tool Resolution Pipeline (`AutoReiv.MCP`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-012):
  - Implemented `ToolRanker` (`src/application/kernel/tool_ranker.py`) with fast sub-millisecond BM25 keyword relevance scoring over tool names, descriptions, and parameter schemas (`[REQ-MCP-004]`).
  - Integrated 3-Tier Tool Resolution in `AgentKernel` (`run_turn` & `stream_turn`), strictly enforcing Tier 1 Hard RBAC, Tier 2 Pinned Core Tools, and Tier 3 Dynamic Tool Ranking when authorized tools exceed `max_active_tools: int = 6` (`[REQ-MCP-004]`).
  - Built `MCPClientAdapter` and `MCPClientManager` (`src/infrastructure/mcp/client_adapter.py`) managing stdio JSON-RPC 2.0 subprocesses, namespace scoping (`mcp_<server>_<tool>`), execution timeouts, and graceful shutdown (`[REQ-MCP-001]`, `[REQ-MCP-002]`, `[REQ-MCP-003]`).
  - Added MCP server management REST endpoints (`GET/POST/DELETE /api/settings/mcp`) and Settings Studio UI panel with connection status badges and auto-mount lifecycles (`[REQ-MCP-005]`).
  - Added portable markdown skill manual parsing via `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) (`[REQ-MCP-006]`).

## [0.14.0] - 2026-08-27

### Changed
- System Simplification: Dual Core Agents, Universal Wiki Skill & System Info Pruning (`AutoReiv.Agents`, `AutoReiv.Skills` & `AutoReiv.Web` - CARD-050):
  - Consolidated built-in baseline agents down to two crystal-clear identities: `assistant` (daily workflow coordinator) and `autoreiv` (self-introspecting platform SRE and codebase expert).
  - Maintained backward-compatibility alias resolution across `SupervisorOrchestrator` and `BuiltinAgentRegistry` for legacy agent IDs (`general-assistant`, `linux-sysadmin`, `librarian`, `system-agent`).
  - Elevated Wiki into a first-class, reusable `WikiSkill` (`src/application/skills/wiki_skill.py`) attachable to both baseline agents and custom user agents in Agent Forge.
  - Pruned obsolete System Info / Docs Studio and associated backend services from the UI, focusing the control plane into a clean 6-studio suite.
  - Passed all 301 Pytest unit & integration tests, 50 Vitest frontend tests, Playwright multi-studio smoke tests, and unified pre-flight verification.
- SQLite State Store Decomposition into Focused Domain Repositories (`AutoReiv.Memory` - CARD-049):
  - Decomposed monolithic 1,559-line `src/infrastructure/memory/sqlite_store.py` into 7 focused domain repository mixins under `src/infrastructure/memory/repositories/` (`sessions.py`, `facts.py`, `settings.py`, `routines.py`, `telemetry.py`, `approvals.py`, `tasks.py`).
  - Isolated SQL DDL and index creation into `src/infrastructure/memory/schema.py` and thread-safe connection management into `src/infrastructure/memory/connection.py`.
  - Maintained 100% public method signatures and return types via `SQLiteStateStore` façade (~34 lines).
  - Verified 100% data persistence and backward compatibility across all 314 tests in under 19 seconds.
- FastAPI Router Decomposition & Architectural Modularization (`AutoReiv.Web` - CARD-048):
  - Decomposed monolithic 1,340-line `src/web/app.py` into 8 focused domain routers under `src/web/routers/` (`chat.py`, `agents.py`, `wiki.py`, `settings.py`, `routines.py`, `observability.py`, `hitl.py`, `system.py`).
  - Reduced `src/web/app.py` application factory to a lean ~170 lines managing lifespan, CORS, static mounts, and dependency attachments.
  - Consolidated multi-agent delegation under `SupervisorOrchestrator` as the unified delegation engine.
  - Verified 100% route and contract compatibility across 314 pytest tests, 50 Vitest unit tests, and Playwright multi-studio smoke suites.

### Added
- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation Orchestration (`AutoReiv.Orchestration`, `AutoReiv.Kernel` & `AutoReiv.Web`):
  - Standardized 5-Key A2A Handoff Envelope (`src/domain/orchestration/models.py`), defining `HandoffEnvelope` (`sender_agent_id`, `recipient_agent_id`, `session_id`, `task_intent`, `context_payload`, `correlation_id`, `depth`, `max_turns`, `timeout_seconds`) and `HandoffResult` (`[REQ-A2A-001]`).
  - Supervisor Orchestration Engine with Recursion & Self-Handoff Guardrails (`src/application/kernel/supervisor_orchestrator.py`), enforcing anti-recursion depth limits (max 2 tiers), circular self-handoff prevention, specialist alias resolution (`sysadmin`, `librarian`, `system`, `general`), and child session isolation (`[REQ-A2A-002]`).
  - Delegate Subtask Tool & Skill (`src/application/skills/delegate_skill.py`), exposing the `delegate_task` tool for registration in `ScopedToolRegistry` (`[REQ-A2A-003]`).
  - Inter-Agent Context Hydration (`src/application/kernel/supervisor_orchestrator.py`), hydrating working memory facts and parameters into delegated prompts (`[REQ-A2A-004]`).
  - Inter-Agent Telemetry & Correlation Tracing (`src/application/telemetry/collector.py`), recording `handoff` spans linking session IDs, correlation IDs, agent IDs, durations, and outcomes (`[REQ-A2A-005]`).
  - REST Multi-Agent Delegation API (`src/web/app.py`), exposing `POST /api/agents/delegate` for external invocation (`[REQ-A2A-006]`).
  - Chat Stream & UI Live Handoff Indicators (`src/application/kernel/agent_kernel.py`, `src/web/app.py`, `src/web/static/modules/studios/chat.js`), streaming `handoff_start` and `handoff_complete` SSE events and rendering animated delegation badges in Chat Studio (`[REQ-A2A-007]`).
  - Comprehensive Multi-Agent Handoff Test Suite (`tests/unit/orchestration/test_handoff_envelope.py`, `tests/unit/skills/test_delegate_skill.py`, `tests/unit/kernel/test_agent_kernel.py`, `tests/unit/web/test_agent_delegation_api.py`) (`[REQ-A2A-001]` - `[REQ-A2A-007]`).


- Human-In-The-Loop (HITL) Interactive State Parking, Action Approval & Resume Engine (`AutoReiv.Kernel` & `AutoReiv.Web`):
  - Domain HITL Models (`src/domain/hitl/models.py`), defining `ApprovalStatus`, `PendingAction`, and `ApprovalDecision` (`[REQ-HITL-001]`).
  - Approval Manager State Parking & Resume (`src/application/hitl/approval_manager.py`), parking agent actions in an in-memory queue with `asyncio.Future` suspension and human-triggered resolution (`[REQ-HITL-002]`).
  - HITL REST API Endpoints (`src/web/app.py`), exposing `GET /api/hitl/pending` and `POST /api/hitl/decide` for human operator interaction (`[REQ-HITL-003]`).
  - Comprehensive HITL Unit & Integration Test Suite (`tests/unit/hitl/test_approval_manager.py`), verifying action parking, approval/rejection resolution, and REST endpoint integration across 6 tests (`[REQ-HITL-004]`).


- Dangerous Shell Command Safety Guardrails & Path Traversal Protection (`AutoReiv.Kernel` & `AutoReiv.Deploy`):
  - Domain Safety Risk Models (`src/domain/safety/models.py`), defining `RiskLevel`, `SafetyViolation`, and `CommandSafetyReport` (`[REQ-GUARD-001]`).
  - Deterministic Command Guardrail Engine (`src/application/safety/command_guardrail.py`), providing rule-based inspection across destructive recursive deletions, disk wiping tools, system shutdowns, fork bombs, and remote pipe-to-shell attacks (`[REQ-GUARD-002]`).
  - Workspace Path Traversal Protection (`src/application/safety/command_guardrail.py`), intercepting path traversal escapes and sensitive OS directory tampering (`[REQ-GUARD-003]`).
  - Subprocess Sandbox Guardrail Interception (`src/application/skills/sandbox_worker.py`), screening all subprocess execution requests and aborting dangerous operations prior to spawning child processes (`[REQ-GUARD-002]`).
  - Comprehensive Safety Guardrails Unit Test Suite (`tests/unit/safety/test_command_guardrail.py`), verifying safety evaluation across 6 tests (`[REQ-GUARD-004]`).


- Ephemeral Subprocess Execution Sandbox & Process Isolation (`AutoReiv.Skills` & `AutoReiv.Deploy`):
  - Workspace File Provisioning & Output Artifact Extraction (`src/application/skills/sandbox_worker.py`), supporting provisioning multi-file input payloads into ephemeral temporary workspaces and extracting generated output files prior to clean teardown (`[REQ-SANDBOX-001]`).
  - Sensitive Environment Variable Scrubbing & Stream Capping (`src/application/skills/sandbox_worker.py`), automatically filtering out host API keys, tokens, and credentials while enforcing standard stream output limits (`max_output_bytes = 1MB`) (`[REQ-SANDBOX-002]`).
  - Agent Sandbox Execution Skill (`src/application/skills/sandbox_skill.py`), exposing the `execute_code` tool for registration in `ScopedToolRegistry` with structured execution telemetry (`[REQ-SANDBOX-003]`).
  - Comprehensive Sandbox Unit & Integration Test Suite (`tests/unit/skills/test_sandbox_worker.py`), verifying workspace file provisioning, output artifact capture, secret scrubbing, timeout killing, and tool execution across 5 tests (`[REQ-SANDBOX-004]`).

- Gateway Resilience Hardening & Streaming Cycle Detection (`AutoReiv.Gateway` & `AutoReiv.Kernel`):
  - Decorrelated Exponential Backoff with Full Jitter (`src/application/gateway/gateway_service.py`), implementing `calculate_backoff` to eliminate synchronized retry storms during transient 5xx and rate-limit errors (`[REQ-RESIL-001]`).
  - Connection Pool Limits & Graceful Lifecycle Teardown (`src/infrastructure/gateway/openai_adapter.py` & `ollama_adapter.py`), standardizing keep-alive connection pools (`max_keepalive_connections=20`, `max_connections=50`, `keepalive_expiry=30.0`) and introducing `async def close()` (`[REQ-RESIL-002]`).
  - Dual-Mode Agent Reasoning & Streaming Cycle Detector (`src/application/kernel/cycle_detector.py` & `agent_kernel.py`), analyzing both repeated tool-call signatures and streaming text phrase loops to halt infinite model loops safely (`[REQ-RESIL-003]`).
  - Comprehensive Gateway Resilience Unit Test Suite (`tests/unit/gateway/test_resilience.py`), verifying backoff bounds, connection pool configuration, and cycle detection break conditions across 4 tests (`[REQ-RESIL-004]`).

- SQLite Episodic Fact Memory Store & Agent Auto-Recall (`AutoReiv.Memory`, `AutoReiv.Skills` & `AutoReiv.Gateway`):
  - Tokenized Substring Fact Search (`src/infrastructure/memory/sqlite_store.py`), implementing `search_facts` filtering across `entity`, `key`, and `value` fields with confidence thresholding and ranking (`[REQ-EPISODIC-001]`).
  - Dynamic Memory Context Formatting & Auto-Recall (`src/application/skills/memory_skill.py`), implementing `render_memory_context` and `auto_recall` generating clean Markdown context blocks for agents (`[REQ-EPISODIC-002]`).
  - Automated Kernel Memory Injection (`src/application/kernel/agent_kernel.py`), transparently enriching agent system instructions with matching cross-session episodic memory facts during synchronous and streaming turn execution (`[REQ-EPISODIC-003]`).
  - Episodic Memory Management REST API (`src/web/app.py`), exposing `GET`, `POST`, and `DELETE` endpoints under `/api/memory/facts` (`[REQ-EPISODIC-004]`).
  - Comprehensive Unit & Integration Test Suite (`tests/unit/memory/test_episodic_memory.py`), validating store CRUD, search filtering, Markdown rendering, kernel auto-recall injection, and REST endpoints across 4 test suites (`[REQ-EPISODIC-005]`).

- Context Window Compaction & Sliding Dynamic Token Budget Strategy (`AutoReiv.Kernel`):
  - Model-Aware Dynamic Token Budgeting (`src/application/kernel/context_compactor.py`), implementing `get_model_context_limit` mapping model families (8k, 32k, 128k, 1M) and enforcing a 75% safety ceiling to prevent context overflows (`[REQ-COMPACT-001]`).
  - Root User Intent Preservation (`src/application/kernel/context_compactor.py`), locking the initial user prompt alongside the system directive during sliding window summarization to eliminate task amnesia in long-running agentic loops (`[REQ-COMPACT-002]`).
  - Structured Compaction Telemetry (`src/application/kernel/context_compactor.py`), introducing `CompactionMetrics` and `compact_with_stats` tracking token savings, turn summarization counts, and tool truncation events (`[REQ-COMPACT-003]`).
  - Comprehensive Unit Test Coverage (`tests/unit/kernel/test_context_compactor.py`), validating pattern mapping, intent preservation, and metrics tracking across 5 tests (`[REQ-COMPACT-004]`).

- Error Boundary Toasts & Offline Backend Messaging (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Non-Blocking Accessible Toast Notification Subsystem (`src/web/static/modules/ui/toast.js` & `src/web/templates/index.html`), introducing `showToast` with `info`, `success`, `warning`, and `error` variants, ARIA live region announcements (`polite` / `assertive`), auto-dismiss timers, and dismiss actions (`[REQ-TOAST-001]`).
  - Studio Error Boundary Migration (`src/web/static/modules/studios/forge.js`, `routines.js`, `wiki.js`), eliminating 100% of intrusive browser `alert()` popups in favor of non-blocking visual toasts (`[REQ-TOAST-002]`).
  - Proactive Gateway Connectivity & Recovery Monitor (`src/web/static/modules/ui/toast.js` & `src/web/static/app.js`), polling `/api/health` in the background, rendering a top-level alert banner on disconnect, and triggering reconnect toasts (`[REQ-TOAST-003]`).
  - Toast Subsystem Unit & Smoke Test Suite (`tests/unit/frontend/toast.test.js`), introducing 6 unit tests verifying toast container creation, variant rendering, timer auto-dismissal, and connectivity state transitions (`[REQ-TOAST-004]`).

- Performance Budgets, Module Bundling & First-Paint Optimization (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Kinetic Energy Equilibrium Sleeping (`src/web/static/modules/utils/physics.js` & `src/web/static/modules/studios/wiki.js`), calculating total system kinetic energy on each simulation frame and pausing `requestAnimationFrame` when convergence drops below `0.005`, driving idle CPU consumption to 0% (`[REQ-PERF-001]`).
  - Strict Modal Animation Teardown (`src/web/static/modules/studios/wiki.js`), halting background animation runners immediately upon modal close, dismissal, or note selection (`[REQ-PERF-002]`).
  - First-Paint Module Preloading (`src/web/templates/index.html`), introducing `<link rel="modulepreload">` directives for core ES modules to optimize browser network waterfalls and Time-To-Interactive (`[REQ-PERF-003]`).
  - Performance & Simulation Lifecycle Unit Suite (`tests/unit/frontend/perf.test.js`), adding 7 unit tests verifying kinetic calculations, start/sleep/wake/stop runner state machines, and zero CPU leakage (`[REQ-PERF-004]`).

- Mobile & Keyboard Accessibility Architecture (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - Semantic ARIA Roles & Screen Reader Landmarks (`src/web/templates/index.html` & `src/web/static/modules/utils/accessibility.js`), adding `role="tablist"` navigation, dynamic `aria-selected` toggling, `role="tabpanel"` views, `role="dialog"` modal wrappers, and `aria-live="polite"` chat stream announcements (`[REQ-A11Y-001]`).
  - Modal Focus Trapping & Global Escape Key Dismissal (`src/web/static/modules/utils/accessibility.js` & `src/web/static/app.js`), trapping `Tab` and `Shift+Tab` within active modal dialogs, closing open modals on `Escape`, and restoring user focus (`[REQ-A11Y-002]`).
  - Studio Navigation Arrow-Key Keyboard Controls (`src/web/static/modules/utils/accessibility.js` & `src/web/static/app.js`), enabling `ArrowDown`/`ArrowRight`/`ArrowUp`/`ArrowLeft`/`Home`/`End` cyclical tab switching (`[REQ-A11Y-003]`).
  - Automated Accessibility Test Suite (`tests/unit/frontend/accessibility.test.js`), introducing 10 pure unit tests verifying focus containment, keyboard navigation, and ARIA syncing (`[REQ-A11Y-004]`).

- Steering & Product Documentation Truth Synchronization (`AutoReiv.Docs`):
  - 7-Studio Product Architecture Specification (`steering/product.md`), detailing the operational capabilities of Chat, Routines, Observability, Agent Forge, Settings, Docs, and Wiki & Mind Map studios alongside local-first privacy boundaries (`[REQ-DOCS-005]`).
  - Dual-Runtime Environment & Topology Steering (`steering/tech.md` & `steering/structure.md`), formally documenting the zero-build ES Module frontend architecture, Python 3.12/FastAPI backend, and directory topology (`[REQ-DOCS-006]`).
  - Milestone 10 Formal Closure & Roadmap Alignment (`steering/roadmap.md`), certifying 100% completion of Milestone 10 (v0.10.0 - Quality & Testability) across all 4 work cards with 174 tracked requirements (`[REQ-DOCS-007]`).

- Gateway, Wiki & Settings End-to-End API Contract Integration Tests (`AutoReiv.Gateway`, `AutoReiv.Wiki`, `AutoReiv.Settings`):
  - Multi-Provider Gateway Model Discovery Contract Suite (`tests/integration/test_gateway_contract_api.py`), validating `/api/models/discover` and `/api/settings/presets` across mocked local and cloud providers with fallback resilience (`[REQ-API-001]`).
  - Wiki Studio Vault & Knowledge Graph Contract Suite (`tests/integration/test_wiki_contract_api.py`), exercising full note CRUD lifecycle (`GET/POST/PUT/DELETE /api/wiki/note`), tree traversal, search, mind map graph serialization, and direct chat thread inbox export (`[REQ-API-002]`).
  - Settings Studio Configuration & Secret Masking Contract Suite (`tests/integration/test_settings_contract_api.py`), verifying provider persistence, purpose-to-model matrix assignments, system documentation topics, and zero secret leakage (`[REQ-API-003]`).
  - Hermetic FastAPI Integration Test Fixtures & Runner Integration (`tests/integration/` & `preflight.py`), providing isolated in-memory SQLite and scratch vault testing executing 12 integration tests in < 5s (`[REQ-API-004]`).


- Comprehensive Unit Test Suite for Frontend Pure Logic (`AutoReiv.Web` & `AutoReiv.Deploy`):
  - 2D Physics Layout Engine Extraction & Unit Testing (`src/web/static/modules/utils/physics.js` & `tests/unit/frontend/physics.test.js`), decoupling force-directed graph calculation algorithms from the DOM and validating repulsion, spring attraction, damping, and equilibrium convergence (`[REQ-UNIT-001]`).
  - Reactive State Store Implementation & Testing (`src/web/static/modules/state/store.js` & `tests/unit/frontend/store.test.js`), implementing a lightweight `createStore` factory with mutation isolation, updater callbacks, and listener subscription/teardown mechanics (`[REQ-UNIT-002]`).
  - Comprehensive Boundary Testing for Formatters & Sanitizers (`src/web/static/modules/utils/formatters.js` & `tests/unit/frontend/formatters.test.js`), hardening byte formatting, token counting, timestamp parsing, and HTML escaping against negative values, non-numeric strings, and XSS injection vectors (`[REQ-UNIT-003]`).
  - Fast-Feedback Pure Logic Test Runner Integration (`package.json` & `preflight.py`), scaling Vitest coverage across 27 pure unit tests running cleanly in < 400ms (`[REQ-UNIT-004]`).

- ESLint & Prettier Static Analysis Pipeline for Frontend (`AutoReiv.Deploy` & `AutoReiv.Web`):
  - Flat Config ESLint 9 Integration (`eslint.config.js` & `package.json`), establishing automated static linting with browser/node globals, rules prohibiting unused identifiers, and full ES module validation (`[REQ-LINT-001]`).
  - Prettier Code Formatting Standard (`.prettierrc` & `package.json`), enforcing single quotes, trailing commas (`es5`), 2-space indentation, and 120 print width across frontend files (`[REQ-LINT-002]`).
  - Unified Pre-Flight & CI Frontend Lint Gate (`.agents/skills/rtm-sync/scripts/preflight.py` & `.github/workflows/ci.yml`), integrating `npm run lint:frontend` as stage 3 of the unified 6-stage pre-flight runner and continuous integration pipeline (`[REQ-LINT-003]`).
  - Zero Linting Errors Baseline Sweep (`src/web/static/` & `tests/`), formatting all frontend source modules and resolving all unused variables, empty catch blocks, and missing globals (`[REQ-LINT-004]`).

- Defensive DOM Query & Null-Safety Architecture Across Studio Interfaces (`AutoReiv.Web`):
  - Complete Helper Migration for All Studio Modules (`src/web/static/modules/studios/`), replacing all raw un-scoped `document.getElementById`, `document.querySelector`, and `document.querySelectorAll` queries across `docs.js`, `settings.js`, `observability.js`, `forge.js`, and `wiki.js` with defensive `$`, `$query`, and `$queryAll` helpers (`[REQ-DOM-001]`).
  - Defensive Event Binding & Helper Infrastructure (`src/web/static/modules/dom.js`), adding `$on(targetOrId, event, handler, options)`, `$show()`, `$hide()`, and `$toggle()` utilities with automated null-guarding (`[REQ-DOM-002]`).
  - Strict XSS Sanitization for Dynamic HTML Content (`src/web/static/modules/studios/chat.js` & `forge.js`), passing all dynamic note, agent, and routine attributes through `escapeHtml()` (`[REQ-DOM-003]`).
  - Automated DOM Architecture Static Lint Rule (`tests/unit/frontend/dom_audit.test.js`), establishing a Vitest static test that parses all frontend JavaScript modules and permanently prevents regressions of raw DOM queries outside `dom.js` (`[REQ-DOM-004]`).

- Playwright CI Pre-Flight Gate & Multi-Studio Navigation Smoke Suite (`AutoReiv.Deploy` & `AutoReiv.Web`):
  - GitHub Actions Continuous Integration Workflow (`.github/workflows/ci.yml`), automating Python 3.12, Node 20, Astral UV caching, Ruff, Pytest, Vitest, and Playwright Chromium smoke gates on every push/PR to `main` and `qa` (`[REQ-SMK-001]`).
  - Multi-Studio Deep Navigation & Element Smoke Assertions (`tests/e2e/smoke.spec.js`), expanding Playwright end-to-end smoke coverage across all 7 studios (Chat, Routines, Observability, Forge, Settings, Docs, Wiki) verifying critical anchors attach without error (`[REQ-SMK-002]`).
  - Interactive Studio Mutation Smoke Checks (`tests/e2e/smoke.spec.js`), exercising non-destructive user interactions including manual topic search, 2D physics Mind Map modal launch/close, New Routine modal, and New Note modal (`[REQ-SMK-003]`).
  - Unified Local Pre-Flight CLI Harness (`.agents/skills/rtm-sync/scripts/preflight.py` & `npm run preflight`), providing a single CLI runner executing all 5 static, unit, integration, smoke, and RTM gates in sequence with formatted summary reporting (`[REQ-SMK-004]`).
  - Playwright Failure Artifacts & Diagnostics Capture (`playwright.config.js` & `.github/workflows/ci.yml`), capturing failure screenshots, console logs, and trace archives in `test-results/` uploaded automatically in CI on test failure (`[REQ-SMK-005]`).

- Frontend Modularization Foundation & Baseline Quality Gates (`AutoReiv.Web`):
  - Native ES Module Decomposition (`src/web/static/app.js`, `src/web/static/modules/`, & `src/web/templates/index.html`), deconstructing the 3,800+ line monolithic `app.js` into isolated ES modules partitioned by concern (`dom.js`, `services/api.js`, `state/store.js`, `utils/`, and individual `studios/` for Chat, Routines, Observability, Forge, Settings, Docs, and Wiki) loaded natively via `<script type="module">` (`[REQ-FE-001]`).
  - Isolated Subsystem Initialization (`src/web/static/app.js`), executing each studio initializer in an independent `try/catch` ring within `initApp()` to ensure faults in one studio cannot crash the primary UI or navigation (`[REQ-FE-002]`).
  - Defensive DOM Query Helpers (`src/web/static/modules/dom.js`), introducing `$(id)`, `$query()`, `$queryAll()`, and `safeCreateIcons()` that log informative console warnings on missing elements rather than throwing uncaught `TypeErrors` (`[REQ-FE-003]`).
  - Pure Logic Utility Extraction & Vitest Test Suite (`src/web/static/modules/utils/` & `tests/unit/frontend/`), isolating pure functions (`debounce`, `formatBytes`, `formatTokenCount`, `formatTimestamp`, `escapeHtml`, `storageGet`, `storageSet`) covered by automated unit tests running in < 300ms (`[REQ-FE-004]`).
  - Playwright Zero-Error Page Load & Multi-Studio Navigation Smoke Gate (`tests/e2e/smoke.spec.js` & `playwright.config.js`), establishing automated headless browser smoke testing asserting zero console errors, zero uncaught page errors, and active tab rendering across all 7 studios (`[REQ-FE-005]`).

- Comprehensive Web UI Tab Hydration & Rendering Hardening (`AutoReiv.Web`):
  - Agent Studio Skill Pack Grid Hydration (`src/web/static/app.js` & `src/web/templates/index.html`), ensuring `renderSkillsCatalog()` deterministically hydrates all 7 skill pack categories and 34 tools on initial and repeated visits regardless of memory caching state (`[REQ-FIX-001]`).
  - System Info Topic Navigation & Viewer Resilience (`src/application/web/system_info_service.py`, `src/web/app.py`, & `src/web/static/app.js`), expanding the topic categories index and displaying default architecture manuals with defensive error boundaries and mobile drawer controls (`[REQ-FIX-002]`).
  - Wiki Studio Vault Auto-Selection & Mobile Navigation (`src/web/templates/index.html` & `src/web/static/app.js`), auto-loading the first available note into Markdown preview on tab load, providing accessible mobile drawer toggles, and ensuring visible action buttons (`[REQ-FIX-003]`).
  - Wiki Mind Map & Graph Canvas Robustness (`src/web/static/app.js` & `src/web/templates/index.html`), introducing viewport bounding fallbacks for 2D canvas sizing and sanitized Mermaid diagram rendering (`[REQ-FIX-004]`).
  - Universal Tab Switching Error Quarantine (`src/web/static/app.js`), wrapping all tab loader triggers inside isolated try/catch boundaries within `switchTab()` (`[REQ-FIX-005]`).

- Chat Studio Agent Selection & Provider Model Discovery Fixes (`AutoReiv.Web` & `AutoReiv.Gateway`):
  - Chat Studio Persistent Multi-Surface Agent Switcher (`src/web/templates/index.html` & `src/web/static/app.js`), introducing an inline `#chatTopBarAgentSelect` dropdown directly in the chat topbar synchronized two-way with the sidebar, and persisting the active agent ID in browser `localStorage` across page reloads and tab navigations (`[REQ-UI-001]`).
  - Multi-Preset Model Discovery & Saved Model Retention (`src/infrastructure/gateway/openai_adapter.py`, `src/infrastructure/gateway/ollama_adapter.py`, `src/web/app.py`, & `src/web/static/app.js`), providing dynamic `provider_id` support across all presets (Ollama, OpenAI, OpenRouter, Anthropic, Groq, DeepSeek, Together, vLLM) and preserving saved custom models in dropdowns (`[REQ-UI-002]`).
- System Observability Live Event Stream, System Agent Root Cause Diagnostics & Librarian Inbox Organization (`AutoReiv.Observability`, `AutoReiv.Skills`, `AutoReiv.Wiki`, & `AutoReiv.Web`):
  - In-Memory System Event Logger & REST Log Buffer (`SystemLogBuffer` in `src/application/observability/log_buffer.py` & `GET /api/observability/logs` in `src/web/app.py`), maintaining a thread-safe 1,000-entry ring buffer capturing all server logs, gateway events, tool calls, and error traces (`[REQ-OBS-007]`).
  - Observability Studio Live Event Terminal UI (`src/web/templates/index.html` & `src/web/static/app.js`), featuring a real-time auto-scrolling log console with level filtering (`ALL`, `INFO`, `WARN`, `ERROR`), search filter, pause/resume toggle, and buffer clear action (`[REQ-OBS-008]`).
  - System Agent Diagnostic Skill Pack & Tooling (`SystemAgentSkill` in `src/application/skills/system_agent_skill.py` & `SYSTEM_AGENT_PROFILE` in `src/domain/agents/profiles.py`), equipping the System Agent with `get_recent_errors`, `get_session_transcript`, `get_agent_sessions`, `test_provider_connectivity`, and `get_system_logs` to diagnose agent failures and network timeouts directly in chat (`[REQ-AGENTS-007]`).
  - Librarian Inbox Triage & Organization Engine (`WikiStore.organize_note` in `src/domain/wiki/store.py`, `LibrarianSkill.organize_wiki_note` in `src/application/skills/librarian_skill.py`, & `LIBRARIAN_PROFILE` in `src/domain/agents/profiles.py`), empowering the Librarian to atomically move staged notes from `inbox/` to permanent `notes/<domain>/<topic>/` taxonomy with complete 35-field YAML frontmatter hydration (`[REQ-WIKI-010]`).
- Mobile-First Responsive Layout & Sticky Viewport Overhaul (`AutoReiv.Web`):
  - Dynamic `100dvh` Viewport & Sticky Chat Input Bar (`src/web/templates/index.html` & `src/web/static/app.js`), anchoring root layout height to `100dvh` across mobile browsers, preventing whole-page scroll bouncing, isolating message stream scrolling to `#messagesContainer`, and pinning the prompt textarea bar firmly at the bottom above virtual keyboards (`[REQ-RESP-001]`).
  - Responsive Off-Canvas Split Drawers for Wiki Studio & System Info (`#wikiDrawerPane` & `#docsDrawerPane`), converting desktop sidebars into slide-over mobile drawers with quick toggle buttons (`[📁 Vault Tree]` / `[☰ Topics]`) and automatic auto-collapse upon note/topic selection (`[REQ-RESP-002]`).
  - Mobile Touch Physics Canvas & Fullscreen Modal Sheets (`src/web/static/app.js`), providing single-finger touch drag, two-finger pinch-to-zoom for the 2D Mind Map, and responsive modal sheet sizing across all mobile viewports (`[REQ-RESP-003]`).
- Chat to Wiki Direct Inbox Export & Flat Staging Vault Structure (`AutoReiv.Wiki` & `AutoReiv.Web`):
  - Flat Inbox Staging Engine (`WikiStore` in `src/domain/wiki/store.py` & `WikiService` in `src/application/wiki/service.py`), eliminating priority subfolders (`need_to_do`, `should_do`, `want_to_do`) in favor of direct, zero-friction flat file staging under `data/wiki/inbox/<slug>.md` (`[REQ-WIKI-007]`).
  - Unified Chat-to-Wiki Inbox Artifact Generation (`POST /api/export/wiki` in `src/web/app.py` & `src/web/static/app.js`), routing single message "Save to Wiki" and full conversation "Export to Wiki" actions directly through `WikiService` to generate structured 35-field YAML frontmatter notes in `inbox/` (`[REQ-WIKI-008]`).
  - Flat Inbox Tree Navigation & Simplified New Note Modal (`src/web/static/app.js` & `src/web/templates/index.html`), rendering all staged inbox notes directly under `inbox (Staging) (X)` without intermediate priority group nesting (`[REQ-WIKI-009]`).
- Provider & Model Settings Persistence & Hydration (`AutoReiv.Settings` & `AutoReiv.Web`):
  - Model Choice Persistence Contract (`ProviderSettingsRequest` & `GET /api/settings` / `POST /api/settings/providers` in `src/web/app.py`), persisting `default_model_id` in SQLite and synchronizing with Gateway fallback resolution (`[REQ-SET-007]`).
  - Settings Studio Model Selection Retention & Auto-Hydration (`src/web/static/app.js`), preserving selected model dropdown values across manual saves, provider switching, dynamic catalog queries, and page reloads (`[REQ-SET-008]`).
- Wiki Studio Interactive Obsidian-Style Mind Map & Tree Navigation (`AutoReiv.Wiki` & `AutoReiv.Web`):
  - Nested Degree & Subject Tree Expand/Collapse Engine (`src/web/static/app.js`), rendering Degree Level 1 (`<domain>`) and Subject Level 2 (`<topic>`) folders as independent interactive collapsible buttons with chevrons, open/closed folder indicators, note count badges, and auto-expanded initial discovery state (`[REQ-MIND-001]`).
  - Multi-Dimensional Knowledge Graph Engine & REST API (`WikiStore.get_mindmap()` in `src/domain/wiki/store.py` & `GET /api/wiki/mindmap` in `src/web/app.py`), extracting heterogeneous node entities (Notes, Tags `#tag`, Degree Domains, Subject Topics) and typed relation edges (`wikilink`, `has_tag`, `in_topic`, `in_domain`) (`[REQ-MIND-002]`).
  - Obsidian-Style Interactive 2D Physics Canvas Mind Map Explorer (`#wikiMindMapModal` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring velocity-Verlet Coulomb particle simulation, spring tension physics, live search filtering, entity dimension toggle pills (Notes, Tags, Domains, Topics), repulsion slider, smooth pan/zoom, interactive hover tooltips with note telemetry, and direct click-to-open note navigation (`[REQ-MIND-003]`).
- Wiki Document Management System & Librarian Architecture (`AutoReiv.Wiki`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - Local-First Degree/Class Taxonomy & Scaffolding Engine (`WikiStore` in `src/domain/wiki/store.py`), organizing human documents into `inbox/` (`need_to_do`, `should_do`, `want_to_do`), `notes/<domain>/<topic>/` (Degree/Field Level 1, Subject/Class Level 2), and `resources/` (`operating_manuals`, `templates`) with path jailing (`[REQ-WIKI-001]`).
  - 35-Field Additive YAML Frontmatter Schema Standard & Telemetry Engine (`FrontmatterParser` & `WikiNoteMeta` in `src/domain/wiki/frontmatter.py`), auto-computing immutable timestamp UIDs (`YYYYMMDD-HHMMSS`), word count, and token telemetry ($round(max(chars / 4, words \times 0.75))$) (`[REQ-WIKI-002]`).
  - Non-Destructive Note Modification Engine (`WikiStore.write_note()`), preserving existing YAML metadata and relations while safely updating note content and bumping `last_updated` (`[REQ-WIKI-003]`).
  - Knowledge Graph & WikiLink Extraction Engine (`WikiStore.get_graph()`), parsing `[[wikilink]]` references across markdown bodies to build interconnected network nodes and edges (`[REQ-WIKI-004]`).
  - Upgraded Librarian Skill & Scoped Tool Grants (`LibrarianSkill` in `src/application/skills/librarian_skill.py`), providing tools for `wiki_note_create`, `wiki_note_read`, `wiki_note_update`, `wiki_note_search`, `wiki_note_list`, `wiki_overview`, and `wiki_graph` (`[REQ-WIKI-005]`).
  - Interactive Wiki Studio Web Interface & REST Endpoints (`#view-wiki` in `src/web/templates/index.html`, `src/web/static/app.js`, and `src/web/app.py`), featuring hierarchical tree navigation, markdown preview and editor, YAML Frontmatter Inspector card, new note modal, and knowledge graph visualization (`[REQ-WIKI-006]`).
- System Info Conceptual Knowledge Hub & Architectural Manual (`AutoReiv.Web` & `AutoReiv.Docs`):
  - Curated System Info Topic Catalog & Service (`SystemInfoService` in `src/application/web/system_info_service.py` & `GET /api/system-info/topics`, `GET /api/system-info/topic/{id}`), delivering structured, educational chapters with rich Markdown and interactive Mermaid diagrams (`[REQ-SYST-001]`).
  - System Info UI Sidebar & Interactive Reader (`[ℹ️ System Info]` in `src/web/templates/index.html` and `src/web/static/app.js`), featuring categorized topic groups, real-time search filtering, deep links, and Mermaid Pan-Tilt-Zoom inspection (`[REQ-SYST-002]`).
  - Formal 5-Tier Architectural Hierarchy Reference Manual (`[REQ-SYST-003]`), clearly distinguishing and explaining the interactions between **Agents** (Autonomous Personas), **Workflows** (Multi-step Goal DAGs), **Routines** (Background Cron Jobs), **Skill Packs** (Domain Capability Bundles), and **Atomic Tools** (Pydantic / JSON-RPC Function Contracts).
- Lean Just-In-Time (JIT) Agent Discovery & Isolated Subagent Handoff Engine (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - Just-In-Time (JIT) Agent Directory Indexer (`AgentDirectoryService` in `src/application/orchestration/directory_service.py`), dynamically searching and ranking built-in profiles and custom SQLite agents by capability keywords, specialization summaries, and authorized skill tags without pre-loading fleet manifests into system prompts (`[REQ-ORCH-001]`).
  - Ultralight 2-Primitive Orchestration Skill (`OrchestrationSkill` in `src/application/skills/orchestration_skill.py`), exposing `lookup_agents(query, limit=3)` returning compact Agent Cards (<60 tokens) and `handoff_to_agent(target_agent_id, task_directive, input_payload)` adhering to strict schema contracts (`[REQ-ORCH-002]`).
  - Isolated Context Execution & Anti-Recursion Engine (`HandoffIsolationEngine` in `src/application/orchestration/handoff_engine.py`), executing subagents in clean 0-turn contexts, bounding execution turns (1–10), enforcing a maximum recursion depth limit of 2 tiers, and rejecting circular self-handoff deadlocks (`[REQ-ORCH-003]`).
  - Real-Time Handoff Telemetry & Chat UI Affordance (`src/web/app.py`, `src/web/templates/index.html`, `src/web/static/app.js`), emitting streaming events and rendering live subagent delegation status pills in Chat Studio showing the target agent, directive, and completion state (`[REQ-ORCH-004]`).
- System Documentation Folder Tree Navigation & Interactive Mermaid Pan-Zoom Inspector (`AutoReiv.Web`):
  - Nested Folder Tree Navigation API (`SystemDocumentationService.get_navigation_tree()` in `src/application/web/system_docs_service.py`), organizing platform specifications into milestone subfolders with `requirements.md`, `design.md`, and `tasks.md` children, ADRs, SDLC rules, and RTM metadata (`[REQ-DOCS-001]`).
  - Interactive Collapsible Folder Tree Sidebar UI (`#view-docs` & `renderDocsNav()` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring folder chevron toggles, open/closed folder icons, child file counts, active document highlighting, and real-time deep search filtering (`[REQ-DOCS-002]`).
  - Interactive Mermaid Diagram Hover Overlay & High-Resolution Modal Inspector (`#mermaidZoomModal` in `src/web/templates/index.html` & `src/web/static/app.js`), attaching hover action buttons (`[🔍 Inspect & Zoom]`) to all rendered Mermaid diagrams in documentation and chat streams (`[REQ-DOCS-003]`).
  - Smooth Pan-Tilt-Zoom (PTZ) Engine (`src/web/static/app.js`), supporting mouse-wheel zooming (20% to 500%), click-and-drag canvas panning, zoom toolbar controls (`+`, `-`, `↺ 100% Reset`), and fullscreen toggle (`[REQ-DOCS-004]`).
- Skill Pack Hierarchy, Deterministic Guardrails, and System Documentation Browser (`AutoReiv.Skills`, `AutoReiv.Agents`, & `AutoReiv.Web`):
  - Hierarchical Skill Pack Manifests and Catalog Aggregator (`src/application/skills/manifest.py`), clustering 20+ atomic tools into cohesive, categorized Skill Packs (`Sysadmin`, `Librarian`, `Verification`, `Planning`, `AgentBuilder`, `Orchestration`, `General & Custom`) (`[REQ-SKIL-001]`).
  - Agent Forge Hierarchical Skill Pack UI with Expandable Tool Cards (`#view-agents` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring one-click bundle checkboxes, automatic indeterminate state propagation, and granular tool-level RBAC (`[REQ-SKIL-002]`).
  - Deterministic Agent Specification Guardrail Engine (`AgentProfileGuardrail` in `src/domain/agents/guardrails.py`), enforcing strict invariants across `AgentBuilderSkill`, `POST /api/agents`, and `PUT /api/agents/{id}`: kebab-case regex slug validation, anti-hallucination tool catalog verification, `ModelPurpose` and `AgentTone` domain checking, and 1-50 turn bounding (`[REQ-SKIL-003]`).
  - System Documentation & Specs Navigation REST API (`SystemDocumentationService` in `src/application/web/system_docs_service.py` & `GET /api/docs/nav`, `GET /api/docs/content`), safely indexing repository specs (`docs/specs/`), Architecture Decision Records (`docs/adr/`), SDLC rules, and RTM matrices with strict directory traversal prevention (`[REQ-SKIL-004]`).
  - Control Plane System Documentation & Specs Browser View (`#view-docs` in `src/web/templates/index.html` & `src/web/static/app.js`), featuring a searchable multi-section document tree, real-time query filtering, and rich Markdown rendering with GitHub alerts and code syntax blocks (`[REQ-SKIL-005]`).
- Routine Management, Dual Cron Humanization, and Agent Forge Binding (`AutoReiv.Routines` & `AutoReiv.Web`):
  - Dual Cron Schedule Humanizer & Next-Run Calculator (`src/application/routines/humanizer.py`) bidirectionally translating cron expressions (`0 * * * *`, `*/15 * * * *`, `0 8 * * *`) into clean English (e.g., *"Every 15 minutes"*, *"Daily at 08:00 UTC"*) with next execution ETA countdown calculations (`[REQ-ROUT-001]`).
  - Full Routine REST API CRUD, Toggle, and Trigger Endpoints (`POST /api/routines`, `PUT /api/routines/{id}`, `DELETE /api/routines/{id}`, `POST /api/routines/{id}/toggle`, `POST /api/routines/{id}/run`, `GET /api/routines?agent_id=...`) with built-in baseline routine protection (`[REQ-ROUT-002]`, `[REQ-ROUT-003]`).
  - Routines Studio Management UI (`#view-routines` in `src/web/templates/index.html` & `src/web/static/app.js`) with frequency presets, live humanizer preview, directive prompts, active status badges, and action controls (`[▶️ Run Now]`, `[✏️ Edit]`, `[⏸️ Pause/Resume]`, `[🗑️ Delete]`) (`[REQ-ROUT-004]`).
  - Agent Forge "Assigned Routines" Character Sheet Integration (`#forgeAssignedRoutinesList` in `src/web/templates/index.html` & `src/web/static/app.js`) rendering all standing jobs led by the selected agent with direct run and edit triggers (`[REQ-ROUT-005]`).
- Dynamic Purpose-Based Model Cascade & "Agent Forge" Character Sheet Studio (`AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Web`):
  - 3-Tier Purpose-to-Model Resolution Cascade (`Agent Kernel -> Agent Profile Override -> Purpose Matrix Slot -> Global Default Model`) implemented in `AgentKernel._resolve_model()`.
  - SQLite Custom Agent Persistence & Scoped Registry (`custom_agents` table in `SQLiteStateStore` and `BuiltinAgentRegistry`), supporting full CRUD operations, built-in baseline agent protection, and operator override overlays.
  - System Agent Meta-Builder Skill (`AgentBuilderSkill` in `src/application/skills/agent_builder_skill.py`) exposing `list_available_skills_and_tools`, `propose_agent_specification`, and `save_agent_specification` to `system-agent`.
  - REST Agent Management Endpoints: `GET /api/skills/catalog`, `GET /api/agents`, `GET /api/agents/{id}`, `POST /api/agents`, `PUT /api/agents/{id}`, and `DELETE /api/agents/{id}`.
  - "Agent Forge" Studio Character Sheet SPA UI (`#view-agents` in `src/web/templates/index.html` and `src/web/static/app.js`) featuring compartmentalized RPG character sheet cards (Identity & Avatar, Persona & Tone, Operating Manual System Prompt, Purpose Matrix & Model Override, Authorized Skill Capability Checkboxes, Real-time Lifetime Telemetry Stats).
  - Embedded System Agent AI Architect Co-Pilot with live streaming advice, quick starter chips (K8s SRE, Postgres DBA, Security Auditor), and one-click `[✨ Apply to Sheet]` blueprint synthesis.
- Unified Settings Studio, Provider Presets & Model Matrix (`AutoReiv.Settings` & `AutoReiv.Web`):
  - Standard `ProviderPresetRegistry` (`src/application/settings/presets.py`) providing built-in presets for Ollama, OpenAI, Anthropic Claude, OpenRouter, Groq Cloud, DeepSeek, Together AI, and vLLM / Local with auto-populated default base URLs.
  - Dynamic Model Discovery endpoint `GET /api/models/discover` querying installed and cloud models across active providers with live hardware RAM fit evaluation.
  - Active Default Model Picker in Settings Studio allowing operators to discover models and persist the default platform model.
  - Harmonized Purpose-Based Model Routing (eliminating Hermes jargon) with auto-populated dropdowns bound directly to discovered models.
  - Live Hardware Fit & Sizing Table displaying model parameter size, quantization format, estimated RAM in GiB, and status classification tags (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`, `cloud`).
- Plan-and-Execute Graph Engine & Goal Mode (`AutoReiv.Kernel`, `AutoReiv.Planning`, & `AutoReiv.Web`):
  - Structured `ExecutionPlan` and `PlanStep` domain models (`src/domain/planning/models.py`) with lifecycle states (`pending`, `in_progress`, `completed`, `failed`).
  - `PlanAndExecuteEngine` (`src/application/kernel/plan_engine.py`) deconstructing complex multi-phase user goals into ordered 2-to-6 step milestone DAGs and executing them sequentially with intermediate synthesis.
  - `PlanningSkill` (`src/application/skills/planning_skill.py`) providing dynamic plan modification tools (`mark_plan_step_completed`, `append_plan_step`, `get_active_plan`).
  - REST endpoint `POST /api/chat/goal` for goal formulation and autonomous multi-step execution.
  - Companion Web UI controls (`[✓] 🎯 Goal Mode (Plan Graph)`), `/goal <instruction>` slash command parser, and live visual milestone checklist rendering in chat.
- Reflexive Self-Verification Loops & SRE Health Auditing (`AutoReiv.Kernel`, `AutoReiv.Skills`, & `AutoReiv.Agents`):
  - Deterministic `VerificationSkill` (`src/application/skills/verification_skill.py`) exposing ground-truth assertion tools: `verify_telemetry_consistency`, `assert_json_schema`, and `validate_metric_bounds`.
  - Iterative `ReflexionLoopEngine` (`src/application/kernel/reflexion_engine.py`) catching verification discrepancies, feeding structured critique notes back to the model, and orchestrating multi-turn autonomous refinement loops (up to 3 attempts).
  - Kernel verified execution methods `kernel.run_verified_turn` and integration into `AgentKernel`.
  - Built-in `auditor-critic` agent profile (`src/domain/agents/profiles.py`) specialized in zero-shot adversarial reviews, risk scoring (1-10), and assumption validation.
  - REST endpoints `POST /api/chat/verified` and `POST /api/agents/audit` for verified execution and external audit pipelines.
- Model Context Protocol (MCP) Client Adapter & Dynamic Skill Loader (`AutoReiv.MCP` & `AutoReiv.Skills`):
  - Standard JSON-RPC 2.0 `MCPClientAdapter` (`src/infrastructure/mcp/client_adapter.py`) managing stdio subprocess transports, tool discovery (`tools/list`), and execution (`tools/call`).
  - Dynamic `SKILL.md` parser `DynamicSkillLoader` (`src/application/skills/dynamic_loader.py`) discovering YAML frontmatter and JSON tool manifests.
  - `mount_mcp_tool` integration in `ScopedToolRegistry` dynamically binding MCP tools with RBAC enforcement.
  - SQLite persistent MCP server registry and REST routes `GET /api/mcp/servers` and `POST /api/mcp/servers`.
- Multi-Agent Inter-Agent Handoff Protocol & Supervisor Delegation (`AutoReiv.Orchestration`):
  - Standardized 5-Key `HandoffEnvelope` domain model (`src/domain/orchestration/models.py`) transferring intent and hydrated context across agent boundaries.
  - `SupervisorOrchestrator` (`src/application/kernel/supervisor_orchestrator.py`) managing specialist agent dispatch, execution, and response synthesis.
  - `DelegateSubtaskSkill` (`src/application/skills/delegate_skill.py`) exposing `delegate_task` tool to allow coordinator agents to route sub-problems.
  - `handoff` telemetry spans linking parent session, sender, recipient, and correlation IDs.
  - REST endpoint `POST /api/agents/delegate` for direct external invocation of specialized workflows.
- Ephemeral Subprocess Sandbox & HITL Approvals (`AutoReiv.Safety` & `AutoReiv.Kernel`):
  - `DangerousCommandFilter` (`src/application/skills/command_filter.py`) statically rejecting destructive commands (`rm -rf /`, `dd`, `mkfs`, `format c:`, raw DB drop queries).
  - `SandboxedSubprocessWorker` (`src/application/skills/sandbox_worker.py`) executing CLI commands and Python scripts within isolated temporary directories with strict timeouts and cleanup.
  - `is_high_risk` tool metadata and `HITLApprovalEngine` (`src/application/kernel/hitl_engine.py`) parking execution awaiting human operator decisions.
  - SQLite `pending_approvals` table and REST endpoints (`GET /api/approvals/pending`, `POST /api/approvals/{id}/decision`) to approve or reject parked tool calls.
  - Real-time streaming cancellation endpoint (`POST /api/chat/stream/{session_id}/abort`) to abort in-flight agent reasoning loops.
- Context Window Compaction & Episodic Memory (`AutoReiv.Memory` & `AutoReiv.Kernel`):
  - `ContextCompactor` (`src/application/kernel/context_compactor.py`) implementing sliding-window message preservation, intermediate turn summarization, and large tool output pruning (>8000 chars) to prevent context window overflow.
  - `episodic_facts` SQLite table and `EpisodicMemorySkill` (`src/application/skills/memory_skill.py`) storing discrete cross-session facts (user preferences, environment settings).
  - Gateway transient error resilience with localized exponential backoff and randomized jitter in `MultiProviderGateway._execute_with_retry`.
  - HTTP persistent client connection pooling (`httpx.Limits(max_keepalive_connections=20)`) in `OllamaProviderAdapter` and `OpenAIProviderAdapter`.
  - `CycleDetector` (`src/application/kernel/cycle_detector.py`) enforcing repetition trap detection across both synchronous `run_turn` and real-time `stream_turn`.
- Multi-OS Packaging & Bare-Metal / Docker Deployment (`AutoReiv.Deploy`): Unified CLI tool (`autoreiv`), background routine engine server lifespan, Ubuntu systemd daemon, Windows service scripts, and Docker Compose with persistent volume mounts.
- Unified CLI entry point (`src/cli/main.py`) with commands:
  - `autoreiv serve`: Launches FastAPI web server and routine tick engine.
  - `autoreiv status`: Reports host CPU/RAM specs, database connectivity, and registered agents.
  - `autoreiv chat`: Interactive terminal chat loop with live token streaming.
  - `autoreiv routine [list|run]`: Direct terminal management and one-shot trigger of background routines.
- FastAPI `lifespan` context manager running `RoutineScheduler` background task concurrently with web request handling.
- Ubuntu / Debian `systemd` daemon unit file (`deploy/systemd/autoreiv.service`) and automated installer (`deploy/systemd/install_systemd.sh`) optimized for Mini PC bare-metal deployment.
- Windows PowerShell runner (`deploy/windows/run_autoreiv.ps1`), batch runner (`run_autoreiv.bat`), and service registration script (`install_windows_service.ps1`).
- Multi-stage production `Dockerfile` with non-root security user, health check, and `docker-compose.yml` with host volume mounts for persistent database (`./data/autoreiv.db`) and wiki documents (`./data/wiki`).
- Environment variable configuration template (`.env.example`) documenting `OLLAMA_HOST`, `OLLAMA_MODEL`, `OPENAI_API_KEY`, `AUTOREIV_DB_PATH`, `AUTOREIV_WIKI_PATH`, and `PORT`.
- Responsive Web & Mobile Front-Door with Wiki Export (`AutoReiv.Web`): Complete zero-build Single-Page Application (SPA) with real-time SSE streaming, collapsible `<think>` tags, and one-click PARA-Wiki markdown export.
- FastAPI application backend (`src/web/app.py`) providing unified REST and SSE endpoints for agents, sessions, chat streaming, wiki note export, settings matrix, KPI dashboard metrics, and autonomous routine triggers.
- `WikiExportService` (`src/application/web/wiki_export_service.py`) generating formatted markdown documents with YAML frontmatter and enforcing path-jailed security.
- Modern responsive desktop and mobile interface (`src/web/templates/index.html`, `src/web/static/app.js`) with tabbed workflows:
  - 💬 **Interactive Chat**: Live token streaming, reasoning `<think>` toggle bubbles, and real-time tool execution status indicators.
  - 📄 **One-Click Action Buttons**: "Export to Wiki" and "Copy to Clipboard" buttons on both full threads and individual assistant replies.
  - ⏰ **Routines Studio**: Active schedule monitoring, status indicators, and manual "Run Now" execution triggers.
  - 📊 **Observability Dashboard**: High-level platform KPI cards, per-agent resource consumption table, and tool reliability matrix.
  - ⚙️ **Settings Studio**: Live provider model picker, purpose matrix configuration, and interactive hardware RAM fit calculator (with custom specs input for 128GB Nimo PC).
- Observability & KPI Dashboard Backend (`AutoReiv.Observability`): Comprehensive telemetry aggregation, per-agent breakdowns, tool reliability matrices, timeline charts, and structured JSON export.
- `ObservabilityDashboardService` for unified platform KPI calculation (total turns, prompt/completion tokens, avg turn latency, error rate percentage).
- Per-agent segregated KPI breakdown reporting turns, token usage, tool invocations, and error counts.
- `ToolReliabilityMetric` matrix tracking tool call frequencies, failure rates, and average duration.
- Time-series metric aggregation into hourly and customizable timeline buckets.
- `TraceExporter` for structured JSON and session trace dumping without external SaaS dependencies.
- Indexed SQLite analytical queries on `telemetry_spans(agent_id, span_type, created_at)`.
- Settings Studio Engine (`AutoReiv.Settings`): Dynamic live model discovery, purpose matrix routing, and hardware fit estimation.
- Live model discovery on `OllamaProviderAdapter` (`/api/tags`) and `OpenAIProviderAdapter` (`/v1/models`) with parameter size and quant level extraction.
- Hermes-style Purpose-Based Model Routing (`ModelPurposeMatrix`) for `GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, and `FAST` operational roles.
- `HardwareFitCalculator` predicting model RAM footprint (weight bits + KV cache headroom) and classifying host fit (`OPTIMAL`, `RUNNABLE`, `OFFLOADED`, `INSUFFICIENT_MEMORY`) with custom specs overrides (e.g. 128GB Nimo PC).
- `SettingsService` for unified settings key-value management and runtime agent persona/tone/prompt customizations (`AgentCustomization`).
- SQLite persistence tables (`settings` and `agent_overrides`) for zero-loss configuration storage across application restarts.
- Autonomous Routine Engine & Background Scheduler (`AutoReiv.Routines`).
- Declarative `Routine` and `RoutineRun` models with interval and cron schedule configurations.
- SQLite persistence for routine configurations and chronological execution run histories (`routines` and `routine_runs` tables).
- `ScheduleMatcher` for deterministic interval and cron due time calculations.
- `RoutineExecutor` for isolated autonomous session execution via `AgentKernel` and automatic telemetry span recording.
- `RoutineScheduler` with non-blocking async tick loop and manual out-of-schedule trigger API.
- 4 Day-1 default routine manifests: Morning Briefing, Daily System Info, Nightly Note Hygiene, and Hourly SRE Pulse.
- 4 Built-In Agent Manifests (`AutoReiv.Agents`): General Assistant, Linux Sysadmin, Librarian, and System Agent.
- `TaskTrackerSkill` with SQLite-backed task CRUD (`create_task`, `list_tasks`, `update_task_status`, `delete_task`).
- `SysadminSkill` with cross-platform host metrics (`get_system_info`) and asynchronous timeout-protected command execution (`cli_exec`).
- `LibrarianSkill` with YAML frontmatter parser and path-jailed PARA-Wiki note creator (`wiki_note_create`, `wiki_note_read`, `wiki_note_list`).
- `SystemAgentSkill` providing platform health diagnostics, database latency testing, and token usage summaries.
- `BuiltinAgentRegistry` for one-line ecosystem bootstrapping and automatic scoped tool binding.
- Agent Kernel & ReAct execution engine (`AutoReiv.Kernel`) supporting multi-turn tool loops, cycle detection, and max turn budgeting.
- Declarative `AgentProfile` manifest with configurable `AgentTone` prompt directive formatting.
- `ScopedToolRegistry` with strict Role-Based Access Control (RBAC) tool execution permissions.
- `SQLiteStateStore` with WAL mode (`AutoReiv.Memory`) for chronological conversation checkpointer and session management.
- `TelemetryCollector` and `TelemetrySpan` tracking per-agent token usage, tool reliability/error metrics, and global platform KPIs.
- Real-time streaming `KernelEvent` generator for tokens, tool execution starts, tool outputs, and turn completions.
- Multi-Provider LLM Gateway (`AutoReiv.Gateway`) with unified message schema (`ChatMessage`, `Role`, `ToolCall`).
- Abstract `LLMProviderPort` protocol and dynamic provider registry.
- `OllamaProviderAdapter` for local/LAN Ollama execution with streaming and tool calling.
- `OpenAIProviderAdapter` for OpenAI-compatible cloud/local endpoints with SSE streaming.
- `MultiProviderGateway` orchestrator with multi-model fallback execution chains.
- `ReasoningDemuxer` for splitting `<think>...</think>` tokens in real-time streams.
- `GatewayProviderFactory` for zero-boilerplate initialization from environment variables.
- 55 hermetic unit tests with mock HTTP transports and zero outbound network calls.
