# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

- CARD-213 In Review (`AutoReiv.Gateway`, `AutoReiv.Settings`, `AutoReiv.Chat` - CARD-213):
  - **Google Gemini Provider Compatibility & Tool Message Sanitization**: Fixed silent hanging and HTTP 400 errors when using Google Gemini as the LLM provider in Chat Studio (`#view-chat`).
  - **Orphan Tool Call Sanitization**: In `OpenAIProviderAdapter._format_messages()`, unlinked or orphan `role: "tool"` messages without a matching `tool_call_id` in the immediately preceding assistant turn (from past provider runs, approval pauses, or handoffs) are automatically transformed into clean user context notes (`[Tool Output: <name>]: <content>`), preserving full conversational history while preventing Google Gemini's OpenAI endpoint from rejecting calls with `HTTP 400: function_response.name: Name cannot be empty`.
  - **Verified Model Recommendations**: Updated Gemini model catalog in `presets.py` to verified, low-latency models (`gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.1-flash-lite-preview`), deprecating non-existent models (`gemini-3.8-flash`, `gemini-3.5-flash`).
  - **Automatic Obsolete Model Normalization**: Added automatic migration in `src/web/routers/settings.py` and `OpenAIProviderAdapter._format_model_name()` that normalizes dead Gemini model names in stored provider configurations to `gemini-3.6-flash`.

- CARD-212 In Review (`AutoReiv.Settings`, `AutoReiv.Security`, `AutoReiv.Web` - CARD-212):
  - **LLM Provider Hybrid Credential Vault Picker**: Added a hybrid credential source selector (`#provVaultCredSelect`) in Settings Studio allowing operators to link any provider directly to an existing Credential Vault secret or type a direct key.
  - **Direct & Linked Vault Modes**: Selecting an existing Vault credential disables the input field and displays a linked badge (`Linked: <name>`), preventing secret duplication and ensuring single-source-of-truth credential management. Selecting "Direct Secret Input (Auto-Vault)" re-enables direct input to auto-encrypt secrets to `llm-provider-{pid}`.
  - **Live Vault Synchronization**: The credential picker dynamically refreshes when secrets are added, edited, or deleted in the Credential Vault table below.
  - **Dynamic Gateway & Model Discovery Binding**: Backend `POST /api/settings/providers` persists `vault_cred_id`, while `/api/settings` and `/api/models/discover` resolve keys dynamically from the linked Vault credential.

- CARD-211 In Review (`AutoReiv.Settings`, `AutoReiv.Security`, `AutoReiv.Gateway` - CARD-211):
  - **Per-Provider LLM Credentials & Vault Persistence**: Updated `provider_settings` to persist configurations as an independent per-provider map (`gemini`, `openai`, `anthropic`, `ollama`, etc.), ensuring swapping between providers never clears or overwrites saved API keys.
  - **AES-256-GCM Vault Encryption**: Integrated LLM provider secrets with AutoReiv's Credential Vault (`credentials` table). API keys are encrypted at rest with zero plaintext secrets exposed in SQLite settings.
  - **Automatic Legacy Key Migration**: On boot and first load, existing legacy plaintext keys (including active Google Gemini keys) are automatically migrated into encrypted Vault records.
  - **Settings Studio Vault Hydration & Masking**: Changing the Provider Preset dropdown dynamically restores the provider's saved host URL, displays an "Encrypted in Vault" badge (`#provKeyVaultBadge`), and masks saved credentials (`••••••••`) to prevent accidental key exposure while allowing one-click overrides.
  - **Vault-Aware Model Discovery**: Updated `/api/models/discover` to dynamically resolve provider keys directly from the Credential Vault when omitted from client query parameters.

## [0.27.0] - 2026-09-10

- CARD-210 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Themes` - CARD-210):
  - **Enterprise Neutral Chrome & Restrained Theme Accents**: Window shells and focused borders use neutral white/alpha borders (`rgba(255, 255, 255, 0.10)`) and elevation shadows without brand halos. Window titlebar icons retain clean slate chrome (`#94a3b8`).
  - **Enterprise Palette Presets**: Recalibrated preset color models for professional enterprise workstations: Indigo, Slate Graphite, Violet, Warm Sand, and Teal.
  - **Storage Key Upgrade**: Upgraded client theme persistence to `autoreiv.theme.v2` to prevent legacy neon/high-saturation test settings from sticking across browser sessions.

- CARD-209 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Themes` - CARD-209):
  - **Dynamic Stage Wallpaper Theming**: Routed `.desktop-wallpaper` radial gradients and backgrounds through `--theme-brand-glow`, `--theme-bg-surface`, and `--theme-bg-base`, allowing the background desktop stage to transform organically with active themes.
  - **Deep Studio Card & Panel Skinning**: Mapped hosted studio cards, panels, and containers (`.bg-slate-900`, `.bg-slate-950`, `.card-nested`, and border dividers) to `--theme-bg-surface` and `--theme-border`, extending palette colors deeply across all windows (Settings, Observability, Routines, Chat).
  - **Primary Buttons & Metric Highlights**: Mapped primary action buttons (`button.bg-brand-600`, `button.bg-indigo-600`, `.btn-primary`) and text highlights (`.text-indigo-400`, `.text-brand-400`) to `--theme-brand` with calculated high-contrast text (`--theme-brand-contrast`).
  - **Rich Palette Tuning**: Enhanced prebuilt presets with distinctly calibrated dark base and surface tones for Amber Phosphor, Emerald Matrix, Orbital Monochrome, and Obsidian Slate.

- CARD-208 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Settings` - CARD-208):
  - **Theme Customizer and Color Palette Presets**: Added an interactive theme customizer to Settings Studio (`#view-settings` -> `#settingsThemeCard`) with 5 prebuilt themes: AutoReiv Indigo, Orbital Monochrome, Obsidian Slate, Amber Phosphor, and Emerald Matrix.
  - **Slider-Style Custom Palette Tuner**: Implemented custom palette controls with Hue (0-360°), Saturation (0-100%), and Background Tone (0-30%) range sliders allowing real-time color adjustments, dynamic hex display tags, and instant window preview.
  - **CSS Variable Architecture**: Routed desktop window shells, titlebars, dock buttons, and active borders through dynamic CSS custom properties (`--theme-brand`, `--theme-brand-hover`, `--theme-brand-glow`, `--theme-bg-base`, `--theme-bg-surface`, `--theme-border`), providing seamless real-time theme switching without DOM recreation.
  - **Persistence & Reset**: Added browser local storage caching under `autoreiv.theme.v1` with automatic boot restoration and a one-click Reset button to restore defaults.

- CARD-207 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Desktop` - CARD-207):
  - **Sessions Window Studio Cleanup**: Hid the redundant "All Studios" navigation grid (`#sidebarNav`) and close button when opening the Sessions drawer/window in desktop mode, giving the recent conversation history list (`#sessionList`) full vertical space to display and scroll.
  - **Studio Page Vertical Scrolling**: Updated `.tab-view.desktop-view-hosted` layout rules so page-style studio views—including Settings (`#view-settings`), Routines (`#view-routines`), Observability (`#view-observability`), and any scrollable tab views—allow smooth vertical scrolling without clipping content on both desktop floating windows and mobile viewports.
  - **Desktop Window Resize Layer & Corner Handles**: Changed `#desktopWindowLayer` to `display: contents` and elevated window shells and 8-directional resize handles to `win.z + 2` above hosted views (`win.z + 1`), completely eliminating stacking context traps that prevented corner clicks. Attached pointer drag/resize handlers to `window` on interaction to prevent event drop during rapid cursor movements.
  - **Dynamic Sessions Window Stacking & Alignment**: Removed hardcoded `z-index: 50 !important` and replaced `inset: auto` with explicit bounds on `#sidebar`, ensuring conversations embed directly into the draggable `#desktopWin-sessions` window shell. Hid the redundant internal drawer header (`#sidebarDrawerHeader`), leaving a single unified window titlebar with smooth dragging and corner resizing.
  - **Window Clarity & Sharp Text Rendering**: Removed `backdrop-filter: blur(10px)` from `.desktop-window` shell overlay, resolving blur artifacts that softened text and UI elements across all floating windows.

- CARD-206 Done (`AutoReiv.Fleet`, `AutoReiv.Orchestration`, `AutoReiv.Skills` - CARD-206):
  - **Online ACE Proposal Deduplication & Approval Filter**: Hardened `ace_online.py` and `agent_kernel.py` so standard HITL `approval_required:` tool execution pauses are never misclassified as tool execution errors, completely eliminating runaway and duplicate draft skill proposals during agent execution loops (`[REQ-HOMELAB-005]`).
  - **OpenTofu Compiler Diagnostic Extraction**: Added `extract_hcl_diagnostics` to `opentofu_tools.py` parsing both structured JSON and human-readable CLI compiler errors (`tofu validate` and `tofu plan`) into actionable `{file, line, summary, detail, severity}` records, empowering the Homelab Engineer to self-correct HCL syntax errors autonomously (`[REQ-HOMELAB-004]`).
  - **Domain Topology HCL Generator & Network Isolation Invariants**: Implemented `generate_domain_topology_hcl` in `homelab_domain_recipe.py` enforcing strict safety invariants: private isolated `Internal` virtual switch (`DomainSwitch`), 10.10.10.0/24 subnet, and 3 Gen2 VMs (`DC01`, `DC02`, and `FS01`) with static memory and zero modifications or exposure to physical host network adapters (`[REQ-HOMELAB-002]`, `[REQ-HOMELAB-003]`).
  - **Multi-Agent Homelab Domain Workflow Recipe**: Defined the reusable 4-chapter relay recipe `homelab-domain-deployment` (`homelab-admin` -> `homelab-architect` -> `homelab-engineer` -> `homelab-admin`) with strict per-phase success criteria (`[REQ-HOMELAB-001]`, `[REQ-HOMELAB-006]`).
  - **OpenTofu Hyper-V Skill Runbook**: Authored canonical `skills/opentofu-hyperv/SKILL.md` runbook codifying Hyper-V provider syntax, Gen2 VM configurations, compiler-guided self-correction protocols, and dry-run safety gates. Equipped `homelab-engineer` pack with `opentofu-hyperv` (`[REQ-HOMELAB-004]`).

- CARD-205 Done (`AutoReiv.Web`, `AutoReiv.UI`, `AutoReiv.Factory` - CARD-205):
  - **Multi-Window Agent Desktop Adoption**: Formally adopted the OS-style Agent Desktop environment (`#desktopStage`, `#desktopDock`, `#desktopWindowLayer`) on `qa`. Dock launchers open Chat, Wiki, Projects, Agents, Factory, Routines, Observability, Settings, Prompts, and Sessions as draggable, resizable, stackable floating windows.
  - **Factory Orchestrator Constructor Fix**: Assigned `self.store = store` in `FactoryOrchestrator.__init__`, resolving an `AttributeError` that impacted Agent Training Factory background advancement and verification battery phases.
  - **Defensive DOM Architecture Compliance**: Replaced raw `document.getElementById` lookup in `agent-desktop.js` with defensive `$` query helper from `dom.js` satisfying `REQ-DOM-001`. Added `id="${d.id}"` attributes to dock buttons for explicit DOM element targeting.
  - **Modal Layer Elevation**: Elevated all modal dialogs (`aria-modal="true"`) to `z-index: 120 !important` so modal cancellation and confirmation buttons are never intercepted by the bottom application dock.
  - **Automated Smoke Test Modernization**: Modernized Playwright E2E smoke suite (`smoke.spec.js`) to test the desktop dock launchers and multi-window interface across all studios with zero console errors.

## [0.26.0] - 2026-09-09

- CARD-204 Done (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-204):
  - **Pure Chat Runtime Promotion**: Decoupled Goal and Self-Verify execution entirely from agent platform tool schemas. Multi-phase jobs and reflexion critic loops operate strictly as server-side runtimes triggered by Chat Studio toggles (`goalMode`, `selfVerify`).
  - **Retired Planning & Verification from Platform Skills**: Removed `planning` ("Goal Planning Engine") and `verification` ("Logic Verification (Critic)") from `PLATFORM_SKILL_TOOLS`, `PLATFORM_SKILL_METADATA`, and `BUILTIN_TOOL_GROUPS`. Platform skills in Agent Studio Box 1 are strictly the 5 active tool suites (`wiki`, `coordination`, `proposals`, `worker`, `sandbox`).
  - **Pruned Skill Seeds**: Removed `planning` and `verification` from `BUNDLED_PACK_IDS` and deleted their bundled runbooks from `src/infrastructure/skills/seeds/`. Added both to `BLED_AGENT_SKILL_IDS` to ensure automatic pruning from `$DATA_DIR/skills/`.
  - **Prompt Token Savings**: Removed dead tool schemas (`formulate_plan`, `get_active_plan`, `append_plan_step`, `mark_plan_step_completed`, `assert_json_schema`, `validate_metric_bounds`) from agent turn payloads.

- CARD-203 Done (`AutoReiv.Skills`, `AutoReiv.Packs`, `AutoReiv.Data` - CARD-203):
  - **Zero Skill Bleed on Inbound Pack Import**: Removed `_copy_skills_in` from `AgentPackService._import_folder`. Agent pack skills stay strictly isolated under `packs/<agent_id>/skills/` and are never copied into `$DATA_DIR/skills/`.
  - **Pack-Aware Skill Export**: Updated `_copy_skills_out` to read from the agent's dedicated `packs/<agent_id>/skills/` folder first, preventing false dependencies on the platform skills directory.
  - **Platform Skills Isolation**: Hardened `forge.js` `loadPlatformSkills()` to render exclusively the verified `platform_skills` from `/api/skills/catalog`, eliminating fallback polling of `$DATA_DIR/skills/`.
  - **Automated Data Pruning in Resolver**: Added `prune_bled_platform_skills` and `prune_orphan_databases` to `bootstrap_data_dir` to automatically remove historical bled agent skills from `$DATA_DIR/skills/` and unlink 0-byte orphan state/storage database files.
  - **Purged Retired Personas**: Deleted retired persona directories (`coder/`, `critic/`, `inspector/`, `sandbox_runner/`) from `platform-packs/` and cleaned obsolete `fleet.json` and `shared_skills/` discovery logic from `agents.py` and `user_catalog.py`.

## [0.25.0] - 2026-09-09

- CARD-202 Done (`AutoReiv.Web`, `AutoReiv.UI` - CARD-202):
  - **Flat Alphabetized Agent Studio Picker**: Removed `<optgroup>` categorizations ("Primary Specialists" and "Internal / Fleet Workers") from Agent Studio (`#forgeAgentSelect`). All agents are rendered in a single, clean list sorted alphabetically from A to Z.
  - **Simplified Platform vs. Custom Tagging**: Options in the Agent Studio dropdown display only `${name} (Platform)` (for built-in and platform agents) or `${name} (Custom)`, eliminating `[fleet]` and `(Internal)` badge clutter.

- CARD-201 Done (`AutoReiv.Web`, `AutoReiv.Skills`, `AutoReiv.Fleet` - CARD-201):
  - **Strict Platform Primitives in Box 1**: Locked `/api/skills/catalog` `platform_skills` strictly to the 7 core platform primitives (`wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sandbox`), preventing user skills or domain runbooks from ever polluting Box 1.
  - **Platform Skills Leakage Guard in Box 2**: Hardened `AgentPackManifest.derive_compat_lists`, `AgentPackService`, and `_pack_skills_payload` so platform capability IDs (`wiki`, `coordination`) ticked in `allowed_skill` are never synthesized into pack skills or rendered in Box 2 (**Agent Pack Skills & Tools**).
  - **Permanent Platform Skills (Zero Dynamic Filtering)**: Eliminated `pack_owned` filtering in `/api/skills/catalog` and `packOwnedIds` filtering in `forge.js`. All 7 core platform skill primitives are permanently visible in Box 1 (**Platform Skills & Tools**) for every agent.
  - **Strict Two-Box UI**: Removed `#forgeFleetBox` entirely from Agent Studio (`index.html` and `forge.js`). Restored the clean two-tier layout: Box 1 (Platform Skills & Tools) and Box 2 (Agent Pack Skills & Tools).
  - **1:1 Agent to Agent Pack on Disk**: Flattened the nested `platform-packs/homelab/` suite into 5 standard, top-level 1:1 agent pack folders: `homelab/`, `homelab-architect/`, `homelab-engineer/`, `homelab-admin/`, and `homelab-janitor/`. Removed `fleet.json`, `shared_skills/`, and nested `agents/` directories.
  - **Standard Platform Levers**: Homelab coordinator and architect agents leverage standard platform `wiki` tools (`wiki_note_read`, `wiki_note_search`, `wiki_note_create`) and platform `coordination` tools (`delegate_to_fleet_agent`, `lookup_agents`, `handoff_to_agent`), eliminating custom duplicate tools.
  - **Automated Platform Pack Seeding & Sync**: Updated `ALL_PLATFORM_PACK_IDS` and `install_platform_agent_packs` in `platform_packs.py` to automatically seed and synchronize all 5 homelab agents directly into the registry alongside platform core agents.

- CARD-200 Done (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-200):
  - **Inline Skill Runbook Editor Placement**: Updated Agent Studio so clicking "Edit" mounts `#studioRunbookEditor` directly adjacent to the clicked skill row rather than rendering below remote MCP servers and credential cards.
  - **Platform Primitive Seed Runbooks**: Authored canonical Matt Pocock 5-section seed runbooks for `sandbox`, `coordination`, `worker`, `planning`, and `verification` in `src/infrastructure/skills/seeds/` and registered them in `BUNDLED_PACK_IDS`.
  - **Multi-Source Catalog Resolution**: Enhanced `UserSkillCatalog.resolve_pack_scoped_skill_md` to seamlessly resolve platform seeds, fleet shared skills (`shared_skills/`), and nested fleet agents.
  - **Accurate Not-Found Error Reporting**: Fixed `get_user_pack` endpoint so unarchived missing packs report `Pack '<id>' not found.` instead of misleading `Archived pack` text.

- CARD-199 Done (`AutoReiv.Fleet`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-199):
  - **Platform Wiki Skill Restoration & Visibility**: Fixed metadata conflict in `homelab-architect` and hardened the backend catalog endpoint so "Wiki & Knowledge Vault" (`wiki`) is consistently visible and functional in the Platform Skills & Tools container (`[REQ-FLEET-010]`).
  - **Unpolluted Core Platform Skills & Tools**: Removed domain-specific homelab infrastructure tools (`manage-opentofu-hyperv`, `lookup-network-spec`, `lookup-host-spec`) from `PLATFORM_SKILL_TOOLS`, keeping AutoReiv platform core strictly isolated (`[REQ-FLEET-011]`).
  - **Consolidated Multi-Agent Fleet Suite Layout**: Unified the 5 homelab specialist packs and their 3 shared skills under a canonical fleet suite format (`platform-packs/homelab/`) with `fleet.json`, `shared_skills/`, and `agents/` (`[REQ-FLEET-012]`).
  - **Agent Studio Three-Tier Skill Architecture**: Introduced `#forgeFleetBox` ("Fleet Shared Skills & Tools") between Platform Skills and Agent Pack Skills in Agent Studio, displaying fleet-wide shared runbooks and tools with batch select/clear actions (`[REQ-FLEET-013]`).
  - **Contextual Fleet Container Visibility**: Configured `#forgeFleetBox` to automatically appear when inspecting an agent belonging to a fleet and gracefully hide for standalone agents (`[REQ-FLEET-014]`).
  - **Consolidated Fleet Suite Single-Door Import & Export**: Updated `AgentPackService` to detect fleet manifests and seamlessly import and export multi-agent suites and their shared runbooks in one unified operation (`[REQ-FLEET-015]`).
  - **Redundant Wiki Toggle Deprecation**: Removed standalone `[x] Allow Wiki Access` toggle in Agent Studio Card 3 (`#forgeAllowWikiAccessCheckbox`), establishing the Platform Skills & Tools checkboxes as the single source of truth for agent Wiki grants.

## [0.24.0] - 2026-09-09

- CARD-196 Done (`AutoReiv.System`, `AutoReiv.Web`, `AutoReiv.SettingsStudio` - CARD-196):
  - **Installed Version & Runtime Environment Inspection**: Added dynamic version resolution, git commit hash, active branch name, and runtime deployment mode detection (`Git Clone`, `Docker Container`, `Systemd Service`, `Windows Service`, `Standalone`) surfaced in Settings Studio (`[REQ-UPD-001]`).
  - **Configurable Upstream Repository & Tracked Branch**: Implemented SQLite persistence and REST API endpoints (`GET/PUT /api/system/updates/config`) to allow operators to track private forks or mirrors (`[REQ-UPD-002]`).
  - **Automated Upstream Update Check & Changelog Preview**: Created `check_for_updates` endpoint querying upstream GitHub REST API or git remotes with commit distance comparison, release notes, and status indicators (`[REQ-UPD-003]`).
  - **Safe In-App Update Apply with Database Snapshotting**: Built one-click update apply with pre-flight dirty tree guard (`git status --porcelain`), timestamped SQLite backup (`autoreiv.db.bak-<timestamp>`), and fast-forward pull (`git pull --ff-only`) (`[REQ-UPD-004]`).
  - **Non-Git Deployment Guidance and Guardrails**: Added copyable upgrade commands (`docker compose pull && docker compose up -d`) for containerized deployments and abort protections on merge conflicts (`[REQ-UPD-005]`).

- CARD-198 Done (`AutoReiv.Fleet`, `AutoReiv.Orchestration`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-198):
  - **Agent Visibility & Fleet Grouping**: Added `visibility` (`"public"` vs `"internal"`) and `fleet` metadata to `AgentProfile` and `AgentPackManifest`. Chat Studio filters out internal specialist workers while Agent Studio groups them under dedicated fleet sections (`[REQ-FLEET-001]`).
  - **Monolithic Hyper-V Deprecation**: Decoupled the legacy monolithic hyperv agent in favor of modular fleet capabilities and exempted it from chat selectors (`[REQ-FLEET-002]`).
  - **Enterprise IT Homelab Documentation Framework**: Populated standard IT documentation hierarchy (`00-governance`, `10-network`, `20-compute`, `30-identity`, `40-services`, `50-runbooks`, `templates`) strictly under `notes/homelab/` with zero impact to the existing Wiki engine (`[REQ-FLEET-003]`).
  - **Homelab Fleet Roles & Starter Profiles**: Established starter profiles and platform packs for 5 homelab roles (`homelab` Coordinator, `homelab-architect`, `homelab-engineer`, `homelab-admin`, `homelab-janitor`) adhering to the 6-section system prompt blueprint (`[REQ-FLEET-004]`).
  - **Scoped Domain Lookup & Delegation Protocol**: Implemented `lookup_homelab_docs` and `delegate_to_fleet_agent` in `fleet_coordinator.py`, allowing the lead coordinator to inject note context and delegate directives to internal specialists (`[REQ-FLEET-005]`).
  - **OpenTofu Hyper-V Capability & Safe Tool Execution**: Created `manage_opentofu_hyperv` tool supporting plan, apply, destroy, validate, inspect_host, and get_vm_status with safe dry-run simulation mode (`[REQ-FLEET-006]`).
  - **Homelab Fleet Skills & Runbooks**: Authored runbook skills (`lookup-network-spec`, `lookup-host-spec`, `manage-opentofu-hyperv`) adhering strictly to Matt Pocock's 5-section layout and YAML frontmatter (`[REQ-FLEET-007]`).
  - **8-Stage Training Factory Dogfooding**: Programmatically executed AutoReiv's 8-stage Training Factory pipeline on `homelab-engineer`, verifying duration tracking, self-healing loop, and deliverable quality gates end-to-end (`[REQ-FLEET-008]`).

- CARD-197 Done (`AutoReiv.Agents`, `AutoReiv.Factory`, `AutoReiv.Web`, `AutoReiv.Orchestration` - CARD-197):
  - **Socratic Agent Pack Creation Directive**: Upgraded `build-agent-pack` skill and prompt directives with Socratic discovery, asking 3-4 targeted questions (specialization, host environment, safety/approval boundaries, tools needed) and instilling the 6-section system prompt architectural blueprint (`[IDENTITY & ROLE]`, `[DOMAIN BOUNDARIES & REFUSALS]`, `[EXECUTION PROTOCOL]`, `[SAFETY & APPROVALS]`, `[TOOL USAGE RULES]`, `[OUTPUT FORMAT]`) (`[REQ-FACT-046]`).
  - **Specialist Agent Quick-Scaffold Modal**: Added `#forgeNewAgentModal` with manual inputs for ID, display name, role, description, purpose slot, and safety requirements in Factory and Agent Studios, enabling rapid agent definition without conversational overhead (`[REQ-FACT-047]`).
  - **Post-Creation Agent Training Handoff Card**: Implemented an immediate post-creation card in Chat Studio (`[ 🚀 Launch Training in Factory ]` and `[ ⚙️ Open in Studio ]`) enabling seamless one-click routing to Factory Studio pre-scoped with the newly created agent (`[REQ-FACT-048]`).
  - **8-Stage Factory Prompt Registry Refinement**: Upgraded default system prompts across all 8 pipeline stages (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`) with agentic constraints, few-shot schema enforcement, and explicit context tokens (`[REQ-FACT-049]`).
  - **Self-Healing Verification Loop**: Added automatic repair edge (`retry_author`) and execution traceback forwarding from Verify to Author phase, enabling automatic self-healing (up to 2 attempts) before failing a training job (`[REQ-FACT-050]`).
  - **Per-Phase Execution Duration Tracking**: Recorded `duration_ms` on phase packets and rendered duration badges on visual flowchart stepper nodes in Factory Studio (`[REQ-FACT-051]`).
  - **Progressive Disclosure Runbook Standard**: Enforced 5-section progressive disclosure runbook layout (`## Overview`, `## Tools`, `## Order`, `## Pitfalls`, `## Done-when`) with YAML frontmatter in synthesized `SKILL.md` runbooks while preserving backward compatibility (`[REQ-FACT-052]`).
  - **Standardized Tool Return Envelope & Google-Style Docstrings**: Standardized synthesized tools to include Google-style docstrings (`Args:`, `Returns:`, `Raises:`) and structured dictionary return envelopes (`{"status": "success" | "error", "data": ..., "error": ...}`) (`[REQ-FACT-053]`).
  - **Tool Name Collision Guard in Promotion**: Added callable name inspection in promote phase and REST API to prevent duplicate callable names and cross-pack tool name collisions, supporting `allow_overwrite` flag for intentional updates (`[REQ-FACT-054]`).
  - **Tabbed HITL Promotion Deliverable Inspector**: Built tabbed deliverable inspection modal (`#factoryDeliverableModal`) with tabs for Runbook preview, Python tool code, and manifest diff (`pack.json`) for operator pre-promotion verification (`[REQ-FACT-055]`).
  - **Comprehensive Automated Verification**: All 1,048 Python backend tests and 284 frontend unit tests passing cleanly with zero lint errors.

## [0.23.0] - 2026-09-08


- CARD-195 Done (`AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Orchestration` - CARD-195):
  - **Dedicated Agent Training Factory Studio**: Elevated the Agent Training Factory into a first-class, top-level Studio workspace (`#view-factory` / `#factoryStudio`) accessible via the navigation bar (`#navFactory`) and desktop app rail (`#railBtnFactory`).
  - **Single Hub Agent Context Dropdown**: Integrated `<select id="factoryAgentSelect">` directly in the Factory Studio header, dynamically populated from `/api/agents` with `All Agents (Platform View)` and all loaded specialist agents, strictly filtering out internal system agents (`agent_builder`, `agent-builder`) (`[REQ-FACT-040]`).
  - **Agent-Scoped Telemetry & Pre-Scoped Launcher**: Selecting an agent automatically filters historical and active runs, updates status filter counters and active run badges, filters the capability backlog, and turns the primary launch action into `[ 🚀 Train <agent_name> ]` pre-scoped with target ID and starter objectives (`[REQ-FACT-041]`).
  - **Retirement of Agent Studio Training Buttons**: Removed `[Train in Lab]` (`#forgeTrainAgentBtn`) and `[Lab Monitor]` (`#forgeLabMonitorBtn`) from Agent Studio (`#view-forge`), consolidating all training lifecycle, monitoring, and HITL approvals exclusively within Factory Studio (`[REQ-FACT-042]`).
  - **Single-Pick Target Lock & Live Pack Verification in Training Launcher**: Streamlined `#trainAgentHandshakeModal` by removing redundant `<select id="trainAgentTargetSelect">` and `#trainAgentNameGroup`. The launcher directly locks to the selected agent from `#factoryAgentSelect`, rendering an on-disk inspection banner (`Target: <Agent>` with `packs/<agent_id>/`, existing skill count, and registered tool count) to guarantee training augments the target pack without duplicate definitions. In Platform View (`All Agents`), attempting to launch training prompts the operator to pick an agent first (`[REQ-FACT-043]`).
  - **Conversational New Agent Creator in Factory Studio**: Added `[ + New Agent ]` button (`#factoryNewAgentBtn`) directly in the Factory Studio top bar, which smoothly transitions the operator to Chat Studio to converse with AutoReiv to define the new agent's brief, instructions, identity, and tone prior to any capability training (`[REQ-FACT-044]`).
  - **Factory Studio Capability Gap Backlog Consolidation**: Relocated the "Needs Training" capability gap backlog (`#agentTrainingBacklogCard`) from Agent Studio into Factory Studio's Runs & Monitor view, dynamically rendering queued gaps for the selected agent (or all pending gaps in Platform View) with one-click training launch (`[REQ-FACT-045]`).
  - **Pipeline & Phase Prompts Sub-View**: Built visual 8-stage interactive flowchart canvas and Phase Prompt Inspector with read-only runtime context variable tokens (click-to-insert `{{seed_intent}}`, `{{objectives}}`, etc.), live prompt editing, platform-level SQLite persistence via REST API, and built-in default resetting.
  - **Training Runs & Live Monitor Sub-View**: Implemented a responsive two-pane layout with search filtering, status tabs (All, In Progress, Needs Review, Completed, Failed), an 8-stage visual progress stepper, HITL human-in-the-loop deployment gate with approved tools promotion, artifact preview modal triggers, and streaming packet activity feed with copy-to-clipboard.
  - **Mobile & Desktop Responsive Design**: Designed with mobile-first breakpoint adaptations, including an intuitive back-to-runs navigation button (`#factoryMobileBackToRunsBtn`) for small screens and sticky controls.
  - **Full Automated Verification & Zero Quality Gaps**: Added and verified comprehensive test suites in `tests/unit/frontend/factory_studio.test.js`, `tests/unit/frontend/train_agent_handshake.test.js`, and `tests/unit/frontend/auto_train_backlog.test.js` (276 frontend tests passing 100%), full Python test suites (107 tests passing 100%), zero eslint errors, zero ruff errors, and full RTM validation for `[REQ-FACT-034]` through `[REQ-FACT-045]`.

- CARD-175 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.HITL` - CARD-175):
  - **Agent Training Factory Instruction Registry & Dynamic Resolution**: Implemented backend system prompt registry and runtime customization for all 8 training phases (`Intent Distill`, `Ground`, `Blueprint`, `Author`, `Scenario`, `Code Verify`, `Optimize`, `Promote`).
  - **SQLite Prompt Persistence & REST API**: Created `src/application/agent_training_factory/prompt_registry.py` managing `factory_phase_instructions` table in SQLite, and REST endpoints `GET`, `PUT`, `DELETE` at `/api/agent_training_factory/phases/instructions` and `/api/agent_training_factory/phases/{phase_id}/instructions`.
  - **Dynamic Phase Runner Integration**: Updated factory phase runners (`intent_distill.py`, `ground.py`, `blueprint.py`, `author.py`, `optimize.py`) to query dynamic system prompts via `get_phase_system_prompt(phase_id, db_path)`.
  - **Drawer Streamlining & Studio Path**: Kept the Lab Monitor drawer focused strictly on real-time activity and HITL deployment, delegating the dedicated visual prompt inspector and flowchart canvas to the dedicated Factory Studio (`CARD-195`).
  - **Agent Studio Action Hygiene**: Removed redundant `[Train New]` button from the Agent Studio header per operator direction, keeping `[Train in Lab]` on active agents.
  - **Full Automated Verification**: Added Python registry tests and REST API router tests, passing 100% with zero linter errors.

- CARD-122 Done (`AutoReiv.SDLC`, `AutoReiv.Developer` - CARD-122):
  - **Three Beats Alignment Protocol Embedded in Developer Agent**: Formally closed CARD-122, validating that the Three Beats working agreement is operationalized directly in the Developer Agent's `plan` runbook (`platform-packs/developer/skills/plan/SKILL.md`), canonical card templates (`card.template.md`), and the Master Constitution (`AGENTS.md` & `GEMINI.md`). Preserved strictly within the Developer Agent and SDLC workflow with zero external skill bloat.

- CARD-155 Done (`AutoReiv.SDLC`, `AutoReiv.Developer` - CARD-155):
  - **Open Standards Constitution & Rules Adoption**: Adopted the canonical DotAgents Protocol (`.agents/`) and `AGENTS.md` open standard for project constitutions and agentic rules under CARD-190, formally closing CARD-155. Intentionally excluded vendor-specific instruction files in favor of unified, vendor-neutral open standards for the Platform Developer Agent.

- CARD-149 Done (`AutoReiv.Agents`, `AutoReiv.Packs`, `AutoReiv.Memory` - CARD-149):
  - **Finance Specialist Agent Pack with Transaction Tracking**: Verified Personal Finance Lead user pack (`packs/finance`) with dedicated SQLite storage (`finance_storage.db`), `personal_finance` runbook, and tools for transaction ingestion (`log_transactions`), category budgeting (`manage_budget`), savings targets (`set_savings_goal`), and financial health reporting (`summarize_finances`).
  - **Isolated Storage & Automated Proof**: Confirmed 100% test pass in `tests/unit/orchestration/test_finance_agent_e2e.py` validating that personal ledger data remains fully isolated in `$DATA_DIR/packs/finance/` without modifying core `autoreiv.db`. Per operator direction, maintained as private user agent state external to git.

- CARD-193 Done (`AutoReiv.Deploy`, `AutoReiv.Docker` - CARD-193):
  - **Linux Systemd Service Uninstaller**: Created `deploy/systemd/uninstall_systemd.sh` providing clean automated uninstallation that stops and disables `autoreiv.service`, cleans up service unit files, removes `/opt/autoreiv`, and preserves `/var/lib/autoreiv` persistent storage by default unless `--purge-data` is explicitly passed.
  - **Linux Systemd Service & Installer Alignment**: Modernized `deploy/systemd/autoreiv.service` to declare single canonical `Environment="AUTOREIV_DATA_DIR=/var/lib/autoreiv"`. Updated `deploy/systemd/install_systemd.sh` to initialize directory layout and sync `templates/` into the installation tree.
  - **Windows Service Uninstaller**: Created `deploy/windows/uninstall_windows_service.ps1` with Administrator privilege checking to safely stop and unregister `AutoReivService` via NSSM with fallback to `sc.exe delete`, preserving local app data.
  - **Docker & Docker Compose Modernization**: Updated `Dockerfile` to copy `templates/` into `/app/templates/` with `autoreiv:autoreiv` ownership for Developer Agent project scaffolding, and provisioned `/data` subdirectories. Modernized `docker-compose.yml` by removing obsolete top-level `version: '3.8'` and verifying persistent volume mounts.
  - **Deploy Suite Documentation & Verification**: Added comprehensive operator manual in `deploy/README.md` and automated test suite in `tests/unit/deploy/test_deploy_suite.py`.


- CARD-189 Done (`AutoReiv.Skills`, `AutoReiv.PlatformPacks`, `AutoReiv.Agents`, `AutoReiv.Web` - CARD-189):
  - **Retirement of `propose_workflow` Tool**: Removed obsolete `propose_workflow` tool registration and handler from `AgentBuilderTools` (`agent_builder_tools.py`) and `skill_proposals.py`. Removed `propose_workflow` from Platform skill `proposals` in `schema.py`, builtin tool groups in `manifest.py`, and allowed tool lists on `AGENT_BUILDER_PROFILE` (`profiles.py`), `platform-packs/assistant/pack.json`, and `platform-packs/autoreiv/pack.json`.
  - **Unified Capability Proposals Platform Skill**: Collapsed the duplicate `recommend-capability` runbook and `proposals` tools container into a single unified Platform Skill: `proposals` ("Capability Proposals & Discovery"). Relocated the seed runbook to `src/infrastructure/skills/seeds/proposals/SKILL.md` and updated `BUNDLED_PACK_IDS`. Added automatic cleanup of legacy `recommend-capability` folders during startup seeding, eliminating the redundant empty skill row from Agent Studio and connecting the 7 proposal tools directly to their operating runbook.

- CARD-192 Done (`AutoReiv.SDLC`, `AutoReiv.Developer`, `AutoReiv.Skills` - CARD-192):
  - **Developer Agent End-to-End Verification**: Supervised the Developer agent across a complete 10-feature real-world project (`SentinelPulse`) built inside `agentic-test` with zero external wheel dependencies (`[REQ-DEVVER-001]` - `[REQ-DEVVER-012]`).
  - **Strict TDD & SOLID Verification**: Followed red-green-refactor TDD on all 10 vertical slices (`models.py`, `storage.py`, `probes.py`, `rules.py`, `alerts.py`, `remediation.py`, `circuit_breaker.py`, `diagnostics.py`, `reporter.py`, `cli.py`), achieving 35/35 passing automated tests and zero ruff lint errors (`[REQ-DEVVER-012]`).
  - **Project Scaffolding .gitignore & Git Repository Initialization**: Enhanced `ProjectsService.create_project` to automatically initialize git repository (`git init -b main`) on project scaffolding and added standard `.gitignore` to `REQUIRED_SCAFFOLD` and `templates/sdlc-project/` to prevent bytecode and cache clutter (`[REQ-DEVVER-001]`).
  - **GitTools Conventional Commit Message Alias**: Updated `GitTools.git_commit` to accept `message` as an alias for `subject`, preventing unexpected keyword argument runtime exceptions when agents invoke git commit tools (`[REQ-DEVVER-011]`).

- CARD-191 Done (`AutoReiv.Web`, `AutoReiv.Projects` - CARD-191):
  - **Active Project State & Explicit Selection**: Upgraded Projects Studio project rows with an explicit "Set as Active" action button and persistent `[Active Project]` green indicator badge (`[REQ-PROJ-010]`).
  - **Two-Pane Workspace Layout**: Expanded Projects Studio from a simple list into a full dual-pane web workspace with Directory Explorer on the left and Artifact Viewer on the right (`[REQ-PROJ-011]`).
  - **Directory Tree Navigation & Quick Filters**: Implemented collapsible folder navigation with file-type iconography and quick category filter buttons for **All**, **Cards** (`.agents/cards/`), **Specs** (`.agents/specs/`), **Steering** (`.agents/steering/`), and **ADRs** (`.agents/adr/`), plus real-time search filtering (`[REQ-PROJ-012]`).
  - **Artifact & File Viewer**: Added rich viewer rendering formatted Markdown via `marked` for cards/specs and styled monospace views for code scripts (`.py`, `.ps1`, `.json`, etc.) with file path breadcrumbs, character counts, and one-click path copying (`[REQ-PROJ-013]`).
  - **Mobile Responsive Reading & Touch Scrolling**: Clamped directory tree height on mobile (`max-h-48`) with independent touch scrolling, added mobile tree collapse/expand toggle controls, and auto-focused the reading pane with full-height scrolling on file selection (`[REQ-PROJ-011]`, `[REQ-PROJ-013]`).
  - **Jailed Project File API Endpoints**: Implemented secure `GET /api/projects/files/list` and `GET /api/projects/files/read` endpoints strictly clamped inside the active project root, filtering out `.git`, `__pycache__`, and `node_modules` (`[REQ-PROJ-014]`).

- CARD-190 Done (`AutoReiv.SDLC`, `AutoReiv.Skills` - CARD-190):
  - **DotAgents Protocol Directory Standardization**: Adopted the open DotAgents Protocol (`.agents/`) as the canonical project-level directory convention, eliminating artifact fragmentation (`[REQ-SDLC-060]`).
  - **Dual-Path SDLC Resolution**: Enhanced `CardTools` with dual-path resolution to prioritize `.agents/cards/`, `.agents/specs/`, and `.agents/steering/` while seamlessly falling back to legacy `.github/cards/` and `docs/specs/` (`[REQ-SDLC-061]`).
  - **AWS Kiro Steering & 3-File Specs**: Integrated AWS Kiro persistent steering (`product.md`, `tech.md`, `structure.md`, `roadmap.md`) and 3-file specifications (`requirements.md`, `design.md`, `tasks.md`) under `.agents/` (`[REQ-SDLC-060]`).
  - **Standardized Artifact Templates with Three Beats**: Created standard templates in `templates/sdlc-project/.agents/templates/` embedding the Three Beats operating instructions (`card.template.md`, `requirements.template.md`, `design.template.md`, `tasks.template.md`, `adr.template.md`) (`[REQ-SDLC-062]`).
  - **Constitution & SDLC Invariants**: Updated `AGENTS.md` and `GEMINI.md` to document the canonical `.agents/` directory standard and AWS Kiro framework (`[REQ-SDLC-063]`).

- CARD-181 Done (`AutoReiv.Agents`, `AutoReiv.PlatformPacks`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-181):
  - **Shipped Platform Developer Agent**: Created `platform-packs/developer` (Schema 1.1) equipped with modular `plan`, `build`, and `test` skills, automatically seeded into `$DATA_DIR/packs/developer/` on launch (`[REQ-DEV-001]`, `[REQ-DEV-003]`).
  - **Unified Multi-Language Engineering Toolset**: Equipped Developer with full engineering tools (`read_project_file`, `write_project_file`, `list_project_dir`, `cli_exec`, `execute_code`, git tools, card tools), enabling shell execution for PowerShell Pester/PSScriptAnalyzer, Python pytest/ruff, and TypeScript vitest (`[REQ-DEV-002]`).
  - **Agent Studio & Chat Presentation**: Configured Developer to display with `[Platform]` badge and enabled chat visibility (`show_in_chat=true`) (`[REQ-DEV-004]`).
  - **Retirement of SDLC Trio**: Retired `conductor`, `coding`, and `review` from active catalog and hid them from chat pickers (`[REQ-DEV-005]`).
  - **Active Selected Project Root Resolution**: Bound `SysadminTools` (`cli_exec`) to `ProjectsService.resolve_root` with optional `cwd` parameter, and injected active project context into `AgentKernel` prompt assembly, ensuring scripts and CLI commands execute directly within the active project directory selected in Projects Studio.

- CARD-188 Done (`AutoReiv.Web`, `AutoReiv.Security`, `AutoReiv.Settings` - CARD-188):
  - **Operator Credential Secret Reveal Endpoint**: Added `GET /api/vault/credentials/{cred_id}/reveal` endpoint returning decrypted secrets for operator verification (`[REQ-VAULT-006]`).
  - **Settings Studio Credential Edit Flow**: Added row edit button pre-populating the credential modal form and supporting retention of existing encrypted secrets when updating metadata (`[REQ-VAULT-007]`).
  - **Settings Studio Sensitive Field Unmask Controls**: Added eye toggle buttons to reveal and re-mask secrets in the table and toggle password visibility in the input form (`[REQ-VAULT-008]`).
  - **Settings Studio Remote Host Edit Flow**: Added row edit button pre-populating the remote host modal form and enabling full modification of host parameters (`[REQ-REMOTE-006]`).

- CARD-160 Done (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Web`, `AutoReiv.Settings` - CARD-160):
  - **Remote Host Profile Persistence**: Added SQLite `remote_hosts` repository and migrations linking remote SSH endpoints directly into the encrypted Credential Vault (`[REQ-REMOTE-001]`).
  - **REST API for Remote Host Management & Probes**: Built `/api/remote_hosts` endpoints (`GET`, `POST`, `DELETE`, and `POST /{id}/test`) supporting connection configuration and in-memory connection latency probes (`[REQ-REMOTE-002]`).
  - **Settings Studio Remote Hosts UI**: Added dedicated Remote Hosts management card and modal in Settings Studio, complete with host listings, connection handshake testing, and deletion controls (`[REQ-REMOTE-003]`).
  - **Platform Remote Execution & Inspection Tools**: Implemented `ssh_exec_command`, `ssh_read_file`, and `ssh_inspect_environment` platform tools for remote machine management without writing temporary private keys to disk (`[REQ-REMOTE-004]`).
  - **Security Guardrails & Access Control**: Enforced agent credential grant verification (`allowed_credentials`), dangerous command blocking via filter checks, and full compatibility with human-in-the-loop approval cards (`[REQ-REMOTE-005]`).

- CARD-168 Done (`AutoReiv.Security`, `AutoReiv.Agents`, `AutoReiv.Kernel`, `AutoReiv.Web` - CARD-168):
  - **Encrypted Local Credential Storage**: Built AES-256-GCM encrypted `CredentialVault` domain engine and SQLite `credentials` repository, automatically creating and storing a 256-bit local master key under `$DATA_DIR/.vault_key` (`[REQ-VAULT-001]`).
  - **REST API for Credential Management**: Added `/api/vault/credentials` endpoints (`GET`, `POST`, `DELETE`) with strict secret masking on read (`****...abcd`) (`[REQ-VAULT-002]`).
  - **Agent Studio Credential Grants**: Added Credential Vault management UI in Settings Studio and per-agent direct credential grants list with live counter badge in Agent Studio, persisted into agent profiles and `pack.json` under `allowed_credentials` (`[REQ-VAULT-003]`).
  - **JIT Tool Execution Injection**: Extended `ScopedToolRegistry.execute()` to dynamically resolve authorized secrets for the active agent, injecting them into tool context (`_tool_context["credentials"]`) and ephemeral environment variables (`AUTOREIV_CRED_<KEY>`), popping them in a `finally` block (`[REQ-VAULT-004]`).
  - **Real-Time Secret Output Scrubbing**: Added `TranscriptScrubber` integrated into `AgentKernel` (`execute_and_scrub_tool`), scanning and masking all plaintext secret occurrences with `***MASKED***` across tool stdout/stderr, message histories, and LLM payloads (`[REQ-VAULT-005]`).

- CARD-187 Done (`AutoReiv.Chat`, `AutoReiv.Routines`, `AutoReiv.Web` - CARD-187):
  - **Human-Readable HITL Code & Command Preview**: Added `formatHitlArgs` in `src/web/static/modules/studios/chat.js` to extract primary script and command arguments (`code`, `command`, `CommandLine`, `script`, `sql`, `query`, `prompt`), rendering them as unescaped, formatted multiline text with metadata neatly listed above, replacing raw JSON stringification with escaped `\n` (`[REQ-HITL-050]`).
  - **Direct Standard Output Display**: Added `formatHitlOutput` in `chat.js` and updated `submitHitlDecision` to extract `stdout` / `stderr` directly. Formats terminal outputs and automatically pretty-prints embedded JSON strings with indentation and real line breaks, eliminating `\r\n` escaping (`[REQ-HITL-051]`).
  - **Routine API Built-in Flag Parity**: Updated `GET /api/routines` in `src/web/routers/routines.py` to check `BUILTIN_ROUTINES` and return `is_builtin: boolean` on each routine (`[REQ-ROUTINE-050]`).
  - **Universal Routine Deletion & Toast Feedback**: Rendered functional Delete button on all routine cards in `src/web/static/modules/studios/routines.js`. Added confirmation dialog checks, direct `DELETE /api/routines/{id}` invocation, grid refresh, and floating toast feedback (`showToast`) (`[REQ-ROUTINE-051]`, `[REQ-ROUTINE-053]`).
  - **Unrestricted Database Routine Deletion & Startup Seeding Guard**: Removed artificial `builtin_ids` deletion rejection from `src/infrastructure/memory/repositories/routines.py`, allowing operators to delete any routine from SQLite storage. Updated `src/web/app.py` and `scheduler.py` to seed default routines once on initial setup so deleted routines stay deleted across restarts (`[REQ-ROUTINE-052]`).

- CARD-179 Done (`AutoReiv.Chat`, `AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web` - CARD-179):
  - **Smart Goal & Verify Checkbox Coupling**: Checking the Goal checkbox in Chat Studio now automatically pairs with and enables Self-Verify (`#verifyToggle`), ensuring multi-phase execution plans default to active critic verification while preserving operator choice to explicitly untick it (`[REQ-REF-001]`).
  - **Live Reflexion SSE Streaming**: Extended `_apply_verify_gate` in `src/web/routers/chat.py` to stream `reflexion_attempt` and `reflexion_critique` events to the chat SSE queue when running named tool checkers, giving real-time visibility into verification attempts and discrepancy critiques before final resolution (`[REQ-REF-002]`).
  - **Collapsible Reflexion Status Badges**: Unified chat stream reflexion badge rendering with `renderReflexionBadge` in `chat.js`, providing expandable/collapsible details (`.reflexion-badge-toggle` and `.reflexion-details`) for inspection of critic verdicts, checkers, and discrepancy logs (`[REQ-REF-003]`).
  - **Autonomous Mode Suggestion for Multi-Step Prompts**: Added prompt heuristic `isComplexMultiStepPrompt` in `chat.js` and suggestion chip `#chatGoalSuggestionChip` in `src/web/templates/index.html`. Prompts with numbered lists, explicit step markers, or multi-action sequential phrases offer a 1-click upgrade to Goal & Self-Verify mode (`[REQ-REF-004]`).

- CARD-180 Done (`AutoReiv.Chat`, `AutoReiv.Web`, `AutoReiv.Agents` - CARD-180):
  - **Chat Options Drawer Workflow Picker Retirement**: Removed `#workflowPicker` and its loading logic from `chat.js` and `index.html`. The chat options drawer now focuses strictly on execution modes, context budget, and loaded tools (`[REQ-CLEAN-001]`).
  - **Completed Job "Save as workflow" Retirement**: Removed `#saveAsWorkflowBtn` and modal triggers from `chat.js` and `index.html` (`[REQ-CLEAN-002]`).
  - **Chat Stream Endpoint Simplification**: Removed `workflow_id` parameter from `ChatStreamRequest` and stripped workflow recipe instantiation branching from `src/web/routers/chat.py` (`[REQ-CLEAN-003]`).
  - **Agent Studio Workflows Card Retirement**: Removed `#studioWorkflowsList` ("Workflows: Saved multi-step plans") box from `index.html` and deleted `loadAgentWorkflows`, chapter editing, saving, and deletion methods from `src/web/static/modules/studios/forge.js` (`[REQ-CLEAN-004]`).

- CARD-186 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.Skills`, `AutoReiv.Web` - CARD-186):
  - **Visible Training Goal & Intent Input**: Added `#trainSeedIntentInput` field to `#trainAgentHandshakeModal` in `src/web/templates/index.html` and wired in `chat.js` and `forge.js`. If left blank, intent derives cleanly from the first objective rather than injecting generic `"Train capabilities for <slug>"` strings (`[AC-1]`).
  - **Pack-Aware Blueprinting**: Extended `BlueprintPhase` with `_load_existing_pack_info` to inspect `pack.json` when targeting existing agents. Passes existing skills, tools, and SQLite storage into the LLM context and heuristic fallback, anchoring new tools to existing skills and guarding against duplicate `{agent_id}` skills or `manage_{agent_id}` dummy dispatchers (`[AC-2]`, `[AC-3]`).
  - **Data & Analytics Tool Synthesis**: Added data query and analytics actions (`query`, `analyze`, `forecast`, `summary`, `report`) to `_synthesize_generic_python_tool` in `src/application/orchestration/tool_synthesizer.py` for agents with SQLite storage or reporting objectives (`[AC-3]`).
  - **Private Pack Skill Isolation**: Restricted `AgentPackService._import_folder()` skill copying to platform pack IDs, keeping private agent pack skills isolated inside `packs/<agent_id>/skills/` without leaking into the global `$DATA_DIR/skills/` catalog (`[AC-4]`).
  - **Pack-Scoped Runbook Editing**: Updated `UserSkillCatalog` with `resolve_pack_scoped_skill_md` allowing the runbook editor (`GET/PUT /api/skills/user-packs/{pack_id}`) to directly read and write private pack-scoped runbooks (`[AC-5]`).

- CARD-185 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Skills` - CARD-185):
  - **Deliverable Auto-Detection & Existing Pack Expansion**: Enhanced `classify_deliverable_type` in `src/application/agent_training_factory/phases/blueprint.py` to inspect target agent packs (`pack.json`, `mcp/`, `tools/`) when deliverable architecture is set to `"auto"`. Automatically maintains and expands existing MCP servers or native tools rather than guessing from scratch (`[AC-2]`).
  - **Procedural Skill Runbook Only Deliverable**: Added first-class support for `"skill"` deliverable architecture in `BlueprintPhase`, `AuthorPhase`, and `VerifyPhase`, authoring pure operational `SKILL.md` runbooks with zero tools or MCP files (`[AC-1]`).
  - **Distinct Multi-Skill Titles & Content Alignment**: Fixed title and content bleed in `AuthorPhase` where all skills previously inherited the first skill's title and dumped raw user prompt paragraphs. Each skill now generates its own unique title (e.g. `# Hyper-V Unattend Templates` vs `# Hyper-V Checkpoint Lifecycle`) and clean operational SOP objectives (`[AC-3]`, `[AC-4]`).
  - **All-Tools Verification Battery Logging**: Updated `VerifyPhase` battery logging and packet outcomes to enumerate all verified authored tools rather than truncating to the first tool (`[AC-5]`).
  - **MCP Container Rebuild Guidance**: Added container rebuild instructions (`docker build -t autoreiv-<slug>-mcp:latest packs/<slug>/mcp`) to `PromotePhase` gate messages, promote API responses, and promotion packets for operator visibility (`[AC-2]`).


- CARD-184 Done (`AutoReiv.Factory`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Docker` - CARD-184):
  - **Remote MCP Server Pack Scaffolding**: Configured Agent Training Factory `AuthorPhase` to generate a self-contained, zero-internal-dependency MCP package under `mcp/` consisting of dual-mode stdio/HTTP `server.py`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`, `run.ps1`, `run.sh`, and `README.md` (`[REQ-MCP-SCAFF-001]`).
  - **Strict No-Loose-Tools Invariant**: Enforced strict deliverable boundary in `AuthorPhase`, `ScenarioVerifyPhase`, `VerifyPhase`, and `PromotePhase` ensuring that selecting MCP deliverable architecture strictly generates only `mcp/` artifacts and declarative skill runbooks (`skills/`), completely omitting loose `tools/` ad-hoc scripts (`[REQ-MCP-SCAFF-002]`).
  - **Docker Container Execution & Verification**: Built and ran the scaffolded Hyper-V MCP server container (`autoreiv-hyperv-mcp:latest`) on port 8080 over HTTP/SSE, successfully executing remote JSON-RPC 2.0 tool calls and discovering tools over network boundaries (`[REQ-MCP-SCAFF-003]`).
  - **Per-Agent MCP On-Demand Mount Endpoint & UI Control**: Added `POST /api/agents/{agent_id}/mcp/{server_name}/mount` and Agent Studio Inspector "Connect" control to dynamically mount running remote MCP containers into AutoReiv's `ScopedToolRegistry` without restarting the application (`[REQ-MCP-SCAFF-004]`).
  - **Pack Manifest Import & Upsert Parity**: Updated `AgentPackService._upsert_agent` to seamlessly map `mcp_servers` from `pack.json` into `AgentProfile`, ensuring custom and built-in agents automatically retain their configured MCP servers across restarts and reloads (`[REQ-MCP-SCAFF-005]`).

- CARD-183 Done (`AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Infrastructure`, `AutoReiv.Packs` - CARD-183):
  - **Per-Agent Remote MCP Server Architecture**: Scoped Model Context Protocol (MCP) servers directly to individual agent profiles and pack manifests (`pack.json`) instead of global-only settings, establishing external microservices as the primary target (`[REQ-MCP-AGENT-001]`).
  - **Remote HTTP/SSE Client Adapter**: Enhanced `MCPClientAdapter` in `src/infrastructure/mcp/client_adapter.py` with HTTP/SSE transport (`transport="sse"`), remote URL endpoints, custom authorization headers, and JSON-RPC 2.0 dispatch over HTTP without requiring local subprocesses (`[REQ-MCP-AGENT-002]`).
  - **Agent Studio MCP Inspector**: Added `#forgeMcpServersCard` in Agent Studio with live server badges, mount status indicators, tool counts, "Add Remote MCP Server" form supporting both remote SSE and stdio modes, and single-click connection probe testing (`[REQ-MCP-AGENT-003]`).
  - **Agent MCP Management Endpoints**: Created endpoints `GET /api/agents/{agent_id}/mcp`, `POST /api/agents/{agent_id}/mcp`, `DELETE /api/agents/{agent_id}/mcp/{server_name}`, and `POST /api/agents/{agent_id}/mcp/test` with SQLite state store and pack manifest synchronization (`[REQ-MCP-AGENT-003]`).

- CARD-182 Done (`AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Frontend` - CARD-182):
  - **Lab Monitor Retry Training Attempt**: Added `#labRetryJobBtn` ("Retry Training") to the Lab Training Monitor drawer run selector row, allowing operators to immediately re-launch a training run with all prior inputs preserved (agent name, seed intent/objectives, deliverable architecture, constraints, prerequisites, reference docs, and target location) into `#trainAgentHandshakeModal` (`[REQ-LAB-002]`).
  - **Structured Job Inputs Endpoint**: Enhanced `GET /api/agent_training_factory/jobs/{job_id}` in `src/web/routers/agent_training_factory.py` to extract and expose structured `inputs` parsed from the initial orchestrator work packet (`[REQ-LAB-003]`).
  - **Copy Activity Feed Control**: Added `#labCopyFeedBtn` to the Live Activity Feed box header in the Lab Training Monitor drawer, enabling single-click copying of the complete timestamped terminal trace to system clipboard with visual "Copied!" feedback (`[REQ-LAB-001]`).

- CARD-176 Done (`AutoReiv.Orchestration`, `AutoReiv.Infrastructure`, `AutoReiv.Web`, `AutoReiv.Packs` - CARD-176):
  - **Capability Architecture Taxonomy**: Established clear architectural separation between external service Model Context Protocol (MCP) servers, local atomic tools, and procedural skill runbooks (`[REQ-DELIV-001]`).
  - **Reusable Pack MCP Server Micro-Framework**: Implemented zero-dependency `PackMCPServer` in `src/infrastructure/mcp/pack_server.py` with standard JSON-RPC 2.0 stdio transport, `@server.tool` decorator, automatic type annotation introspection, and schema derivation (`[REQ-DELIV-002]`).
  - **Socratic Train Agent Modal Deliverable Inputs**: Added `#trainDeliverableType` selector ("Auto-detect", "Model Context Protocol", "Native Atomic Tool", "Procedural Skill Runbook Only") and collapsible `#trainAdvancedReqsAccordion` with constraints, prerequisites, and reference docs inputs in `src/web/templates/index.html` and `src/web/static/modules/studios/chat.js` (`[REQ-DELIV-003]`).
  - **Agent Studio Badges**: Rendered distinct indigo `[MCP Server]` and slate `[Native Tool]` badges next to capability tools in `src/web/static/modules/studios/forge.js` (`[REQ-DELIV-003]`).
  - **Pack Manifest MCP Server Specification**: Extended `AgentPackManifest` in `src/application/agent_packs/schema.py` with `mcp_server: Optional[PackMCPServerConfig]` and dynamic lifecycle mounting in `src/infrastructure/mcp/client_adapter.py` (`[REQ-DELIV-004]`).
  - **Author Phase Dual Scaffolding**: Integrated deliverable classification in `BlueprintPhase` and scaffolded `mcp/server.py` in `AuthorPhase`, pairing with agentskills.io YAML frontmatter and 5-section imperative SOP skill runbooks (`[REQ-DELIV-005]`).
  - **Verification Battery MCP Subprocess Gate**: Implemented `run_mcp_battery()` in `VerificationBatteryService` and integrated into `VerifyPhase`, validating MCP servers across deterministic stdio execution, invariant safety, idempotency stress replay, and SRE Critic AST audit (`[REQ-DELIV-006]`).
  - **Windows SelectorEventLoop Compatibility**: Refactored `MCPClientAdapter` from `asyncio.create_subprocess_exec` to `subprocess.Popen` in a thread executor with an async lock, resolving the `NotImplementedError` that occurred when running inside Uvicorn on Windows, and improved `critic_notes` error formatting so exceptions never evaluate to blank (`[REQ-DELIV-006]`).
  - **Promote Phase Pack Manifest Persistence**: Saved `mcp_server` configuration to `pack.json` upon job promotion and mounted pack server into `MCPClientManager` (`[REQ-DELIV-007]`).

- CARD-174 Done (`AutoReiv.Architecture`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-174):
  - **Execution Primitives Taxonomy**: Formalized the AutoReiv agentic execution stack (CoT -> ReAct -> Plan & Execute -> Reflexion -> Multi-Agent -> Graphs).
  - **Platform vs. User Pack Boundaries**: Locked platform-owned core anchors (Assistant, Developer, AutoReiv) vs modular User Agent Packs (`$DATA_DIR/packs/`).
  - **Derived Card Scaffolding**: Spawned CARD-179 (Smart Goal & Verify Coupling), CARD-180 (Retire Chat Workflow Picker), and CARD-181 (Platform Core Developer Agent).

- CARD-169 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Architecture` - CARD-169):
  - **Nomenclature Lock**: Locked standard name as **Agent Training Factory** (ATF) and Lab Monitor across all documentation, UI, and code.
  - **Location Semantics Clarification**: Formally defined the path field as strictly an optional read-only reference codebase directory, never writing generated pack files to the project root.



## [0.22.0] - 2026-09-07

- CARD-178 Done (`AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Skills` - CARD-178):
  - **Structured Note Templates**: Added 6 canonical templates (`feynman-technique.md`, `concept-map-system-hub.md`, `dikw-pyramid-of-insight.md`, `zettelkasten-atomic.md`, `sop-runbook.md`, `adr-decision.md`) seeded in `02_Resources/_Templates/` with standard YAML frontmatter and clear step-by-step markdown sections.
  - **Template Endpoints**: Added `GET /api/wiki/templates` and `GET /api/wiki/template?slug=...` REST API endpoints to list and fetch structured template skeletons.
  - **Optional Directive System**: Kept freeform topic synthesis untouched as the default. Templates are strictly optional directives that can be requested naturally in chat or selected from the UI.
  - **New Note Modal Integration**: Added `#newNoteTemplateSelect` dropdown to `#wikiNewNoteModal` defaulting to "None (Freeform Topic Synthesis)". Selecting a template dynamically pre-fills the body textarea with the chosen skeleton.
  - **Agent Tool Support**: Added `wiki_template_list` tool and `template` parameter to `wiki_note_create` for assistants to inspect templates and apply structured frameworks when explicitly requested.


- CARD-177 Done (`AutoReiv.Wiki`, `AutoReiv.Web` - CARD-177):
  - **Collapsible Folders Default Closed**: All top-level sections (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) and nested domain/topic subfolders start collapsed on initial page load and vault reload, with toggle persistence and search-driven auto-expansion.
  - **Select-Then-Delete Navigation Flow**: Clicking a folder row selects it, updates `#activeWikiTitle` and `#activeWikiPath`, renders a Folder Overview card with item count and note links, and activates `#wikiFolderActionsGroup` with `#wikiDeleteFolderBtn` in the main header bar.
  - **Subfolder Deletion (`DELETE /api/wiki/folder`)**: Enabled deleting subfolders directly from the Wiki Studio header toolbar, folder overview card, or tree hover buttons with confirmation prompts and reactive editor cleanup.
  - **Guarded Root Invariant**: Explicitly prohibited deleting foundation root folders (`00_Inbox`, `01_Notes`, `02_Resources`, `03_Archive`) across both the UI (displaying a `#wikiRootFolderBadge` `[🔒 Protected Root]`) and backend validator.

- CARD-173 Done (`AutoReiv.Wiki`, `AutoReiv.Routines`, `AutoReiv.Web`, `AutoReiv.Kernel` - CARD-173):
  - **Platform-Owned PARA-Wiki Standard**: Enforced Jacob's single PARA-Wiki vault layout (`00_Inbox/`, `01_Notes/<domain>/<topic>/`, `02_Resources/_Templates/`, `03_Archive/`) with transparent backwards-compatible path aliasing.
  - **Single-Door Inbox Filing**: All new notes land in `00_Inbox/` with a lightweight 10-field staging YAML frontmatter schema.
  - **Pre-Write Fluff Scrubber**: Added `clean_note_content()` purging conversational AI greetings, sign-offs, and filler while protecting code blocks and technical content verbatim.
  - **Tag Authority Registry**: Seeded `02_Resources/_Templates/tag-authority.md` with check-first normalization and novel tag self-registration.
  - **Wiki Curation Routine**: Autonomous scheduled background routine (`wiki-curation`) and on-demand `[⚡ Curate Inbox Now]` toolbar button to scrub fluff, validate metadata, check/register tags, deduplicate notes, and graduate notes to `01_Notes/`.
  - **Per-Agent Wiki Access Gate**: Added `[x] Allow Wiki Access` toggle in Agent Studio, controlling RBAC access to wiki tools in `ScopedToolRegistry`.
  - **One-Door Policy Hardening for Agent Tools**: Enforced that `wiki_note_create` and the UI new note modal strictly stage new captures into `00_Inbox/`, preventing agent bypasses into `01_Notes/` and ensuring all notes pass through staging and the autonomous curation routine.

## [0.21.0] - 2026-09-06

- CARD-171/172 Factory domain-taint cleanup (`AutoReiv.Orchestration`, `AutoReiv.Web`):
  - Restored domain-agnostic Scenario Verify, Blueprint, Author, Ground, and Optimize phases (gated Hyper-V bleed and tool fragment rules strictly to Hyper-V domains).
  - Restored promotion file selection to cleanly prefer latest Author files map.
  - Fixed `_latest_blueprint` packet lookup order in Author phase.
  - Fixed 14 ruff lint errors and 5 test regressions across unit and web test suites.

- CARD-171/172 Factory quality harden (AutoReiv.Orchestration):
  - **Checkpoint focus** bucket: Checkpoint-VM / Get-VMSnapshot / Restore / Remove only (no New-VM/switch/unattend bleed).
  - **Scenario Verify** fails on out-of-focus action branches / banned tokens (not prose-only; ignores `no oscdimg` constraint echo).
  - **Intent Distill + Ground** generic SOP rubric (purpose / steps / verify / rollback); reject vacuous brief-echo.
  - Author seed-only + re-filter for any `manage_hyperv_*` tool (narrow trains stay narrow).
  - **Negation scrub** so `no switch/NIC` / `No New-VM` do not widen focus; Scenario Verify flags out-of-scope tool files.

- CARD-172 Done (`AutoReiv.Orchestration`, `AutoReiv.Wiki`, `AutoReiv.Frontend` - CARD-172):
  - **Intent Distill** phase (question battery -> structured answers) before Ground.
  - **Scenario Verify** phase (Blueprint capability done-whens) before Code Verify.
  - **Inner rinse** (implementation) -> Author; **outer rinse** (sop/how) -> Intent Distill + Ground with Reflexion lessons; caps `max_verify_rinses` / `max_outer_rinses`.
  - Lab Monitor 8-stage stepper + feed lines for inner/outer rinse reasons.
  - Persist `outer_rinse_count`, `max_outer_rinses`, `failure_class`, `scenario_matrix_json` on FactoryJob.


- CARD-171 Done follow-up (AutoReiv.Orchestration - CARD-171):
  - **Verify multi-skill tool selection**: battery loads exact `tools/<primary>.py` (no sibling overwrite ImportError).
  - **Author seed-only fast path** for Hyper-V multi-skill blueprints (avoid 4x LLM hangs).
  - **Docstring path sanitize** so `D:\` in seed intent does not break generated tool AST.

- CARD-171 Done follow-up (AutoReiv.Orchestration - CARD-171):
  - **Multi-skill Hyper-V blueprints**: Blueprint keeps VM lifecycle / networking / unattend-templates / template-maintenance skills (no single fat manage_hyperv collapse). Author emits all blueprint tools+skills. Promote merges skills/<id>/SKILL.md. Focus synthesizer builders emit real Hyper-V\ cmdlets (New-VMSwitch, Set-VMDvdDrive, Autounattend ISO, template maintenance).
  - **Synthesizer/Author hardeness**: sanitize seed docstring paths (D:/...); Author rejects LLM tool_code that fails  st.parse and restores synthesizer seed.

- CARD-171 Done follow-up (`AutoReiv.Orchestration` - CARD-171):
  - **Non-Hyper-V CLI synthesizer path**: Windows services/sysadmin briefs synthesize `Get-Service` tools + matching SKILL actions (no Hyper-V `Get-VM` costume bleed).
  - **Author domain-bleed gate**: If LLM returns Hyper-V `Get-VM` tool/skill for a Windows services brief, restore synthesizer `Get-Service` seed (CARD-171).
  - **Promote/Optimize files_map preference**: Latest Author `files_map` wins over stale Optimize snapshots so rinsed Get-Service packs are not clobbered by earlier Hyper-V copies.
  - **Safe OBJECTIVES literals**: Generated tool `OBJECTIVES` lists use `json.dumps` so apostrophes in objectives no longer SyntaxError the sandbox battery.

- CARD-171 Done follow-up (`AutoReiv.Orchestration`, `AutoReiv.Frontend` - CARD-171):
  - **Max verify rinses**: `FactoryJob.verify_rinse_count` / `max_verify_rinses` (default 3); Verify fail increments; at max, job status `failed` with packet `critic_notes` (no infinite Author↔Verify loop).
  - **Fail reasons visible**: Verify packet messages include rinse progress + short reason; Lab Monitor live feed shows a `Reason:` line from `critic_notes` via `formatLabPacketFeedLines`.
  - **Path false-positive fix**: Stage-2 preflight no longer bans `"C:\`; uses real `..` traversal / sensitive Unix-path checks so `D:\Archive\...\2022.ISO` and `C:\Users\...` are allowed.
  - **Author adapts**: Latest Verify `critic_notes` injected into Author LLM user context as `LAST VERIFY FAILURE`.

- CARD-171 Done follow-up (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Frontend` - CARD-171):
  - **Live-test grounding/author/verify fix**: Persist `objectives` on `FactoryJob` (SQLite `objectives_json`); create-job copies payload objectives; PhaseContext merges job objectives with orchestrator work-packet facts.
  - **Ground heuristics**: Match `hyperv` (no hyphen), `unattend`/`autounattend`/`iso`/`vhdx`/`template`; force cli + Hyper-V module when keywords match; rich operating manual includes full seed, objectives, and ISO paths (no costume computation/`{slug}-cli` when intent is Hyper-V).
  - **Author quality gate**: Pass objectives into LLM; reject stub `Agent for managing ... tasks` / missing Purpose+Objectives / missing unattend-ISO keywords; enrich SKILL with seed brief.
  - **Verify shallow-stub gate**: `is_shallow_stub_artifact` fails battery when skill/tool ignore seed objective keywords.
  - **Lab Monitor artifact preview**: Clickable `#labArtifactPills` open `#labArtifactPreviewModal` with packet content, pre-promote note, and expected `%LOCALAPPDATA%\AutoReiv\packs\<agent_id>\...` paths.

- CARD-171 Done (`AutoReiv.Orchestration`, `AutoReiv.Wiki`, `AutoReiv.Web`, `AutoReiv.Frontend` - CARD-171):
  - **Agent Training Factory Orchestrator**: Replaced costume `FactoryRunner` (deterministic ToolSynthesizer walker + five persona packs) with `FactoryOrchestrator` under `src/application/agent_training_factory/` — thin phase registry (Ground -> Blueprint -> Author -> Verify -> Optimize -> Promote), rinse edges (Verify fail -> Author), real gateway LLM phase context, Wiki grounding with front-matter contract v1 (`type=factory-grounding`, `agent_id`, `medium`; optional `factory_job_id`/`status`).
  - **Consistent rename**: API prefix `/api/agent_training_factory`, package/modules/UI copy use Agent Training Factory / `agent_training_factory`. Lab Monitor shows six phases (not personas). FE fetch URLs updated.
  - **Persona packs retired from Factory**: `FACTORY_PACK_IDS` emptied; former `{conductor,inspector,coder,sandbox_runner,critic}` recorded as `RETIRED_FACTORY_PERSONA_PACK_IDS` and no longer presented as Factory runtime. Assistant/AutoReiv and unrelated user packs untouched. SQLite `factory_*` tables kept (legacy names documented in code).
  - Surfaces kept: Train Agent, Lab Monitor, Needs Training backlog, auto-train, promote/HITL. Done after review and live test.

## [0.20.0] - 2026-09-05

- CARD-167 Done (`AutoReiv.Web`, `AutoReiv.Frontend`, `AutoReiv.Skills` - CARD-167):
  - **Agent Studio Skill Runbook Editor Close & Cancel Controls**: Added top-right close `x` button (`#studioRunbookCloseBtn`) and bottom `[Cancel]` button (`#studioRunbookCancelBtn`) to the skill runbook editor in Agent Studio (`#studioRunbookEditor`), wired to `hideRunbookEditor()` in `forge.js` to dismiss the editor, clear form inputs, and return the operator to the skills list [REQ-DATA-019, REQ-DATA-020].


- CARD-166 Done (`AutoReiv.Orchestration`, `AutoReiv.Packs`, `AutoReiv.Kernel` - CARD-166):
  - **Module-Qualified Host Cmdlet Tool Synthesis**: Updated `ToolSynthesizer` in `src/application/orchestration/tool_synthesizer.py` and live agent packs to fully qualify all virtualization cmdlets (`Hyper-V\Get-VM`, `Hyper-V\New-VM`, `Hyper-V\Start-VM`, `Hyper-V\Stop-VM`, `Hyper-V\Restart-VM`, `Hyper-V\Checkpoint-VM`, `Hyper-V\Get-VMSnapshot`, `Hyper-V\Remove-VM`, `Hyper-V\Get-VMSwitch`, `Hyper-V\New-VHD`, `Hyper-V\Add-VMHardDiskDrive`) and explicitly import `Import-Module Hyper-V -ErrorAction SilentlyContinue;`, eliminating command lookup shadowing and ambient namespace collisions on the host [REQ-FACT-029, REQ-FACT-030, REQ-FACT-031].
  - **Domain-Agnostic Purpose-Grounded Environment Discovery**: Grounded `_step_discovery_probe` in `factory_runner.py` directly in the agent's purpose, intent, and objectives, dynamically detecting target execution medium (CLI, API, Database, Filesystem, Computation) and inspecting module availability and namespace isolation rules rather than returning static mocks [REQ-FACT-032].
  - **Verification Battery Command Collision Guardrail**: Enhanced the 4-stage verification battery in `verification_battery.py` and `generate_verification_test` to actively detect foreign module command collisions and unhandled subsystem interception signatures in runtime stderr, failing Stage 2 safety with actionable diagnostics before any code is approved for deployment [REQ-FACT-033].

- CARD-164 Done (`AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.HITL` - CARD-164):
  - **Autonomous Background Factory Runner**: Implemented `FactoryRunner` background worker loop in `src/application/orchestration/factory_runner.py` started in `app.py` lifespan to automatically advance queued and active training jobs across all graph nodes to `hitl_deploy_gate_node` without manual intervention during sandbox testing.
  - **AutoReiv Platform Chat Anchoring**: Anchored all training jobs and HITL promotion milestone notifications to the `autoreiv` platform agent's session, guaranteeing that new or headless agents (`show_in_chat: false`) never orphan deployment approval cards.
  - **Lab Monitor Slide-Over Drawer in Agent Studio**: Added `#forgeLabMonitorBtn` with dynamic active runs badge (`#forgeLabRunsBadge`) and a full slide-over `#labMonitorDrawer` featuring an active run selector, a 5-stage visual stepper (Discovery, Blueprint, Toolmaker, Sandbox QA, Deploy Gate), a live packet activity feed, and direct **Approve & Deploy** and **Reject** buttons.
  - **Lab Monitor Drawer Visibility & Handshake Input Alignment**: Fixed DOM nesting in `index.html` by properly closing `agentBrainDrawer` tags so `#labMonitorDrawer` is an independent sibling and slides open immediately when clicked, added auto-open on job launch, added `autocomplete="off"` and input resets to prevent browser pre-filling `admin`, marked project path as optional with OS/hypervisor hints, and added dedicated `#trainAgentNameInput` for training brand new agents from scratch.
  - **Pack Tool Persistence & Registry Mount**: Fixed `promote_factory_job` to extract authored tool files and runbooks from packet payloads, persist `tools/<tool>.py` and `skills/<agent>/SKILL.md` into `$DATA_DIR/packs/<agent_id>/`, register tools under `pack_tool_names` and `allowed_tool_names` in `pack.json`, and register tool dispatch handlers directly in `ScopedToolRegistry` and `master_tool_registry` so promoted agents immediately possess callable tools.
  - **Chat Studio Lab Monitor Link**: Added a direct "View in Lab Monitor &rarr;" trigger inside the Chat Studio training launch bubble, allowing instant transition from chat to the live monitor drawer.
- CARD-165 Done (`AutoReiv.Kernel`, `AutoReiv.Orchestration`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Frontend` - CARD-165):
  - **Agent Studio Autonomous Training Controls**: Added "Allow Autonomous Training" checkbox (`#forgeAutoTrainCheckbox`) and "Max Auto-Train Retries" input (`#forgeMaxTrainRetriesInput`) in Agent Studio, persisted into `pack.json`, `AgentProfile`, `agent_overrides`, and `custom_agents` [REQ-FACT-023].
  - **Turn-Time Missing Capability Detection**: Implemented `CapabilityDetector` identifying missing tools or capability deficiency phrases in agent responses during operational chat turns [REQ-FACT-024].
  - **In-Flight JIT Sandbox Tool Synthesis & Live Telemetry**: Implemented `JitToolSynthesizer` evaluating drafted tools in ephemeral workspaces through the full 4-stage verification battery, bounded by per-agent max retries (1–5, default 2), with real-time `auto_train_progress` status indicators in Chat Studio [REQ-FACT-024, REQ-FACT-025].
  - **Strict 4-Stage Battery HITL Auto-Bypass**: Automatically bypassed HITL deployment gate strictly when all 4 sandbox battery stages pass 100% cleanly, deploying tools to `packs/<agent_id>/tools/<tool>.py`, registering runbooks, and updating live tool registries [REQ-FACT-025].
  - **Seamless Turn Resumption**: Automatically resumed the paused turn upon verified tool deployment, injecting the new tool into active context so the agent completes the original user request without manual re-prompts [REQ-FACT-026].
  - **Capability Gap Backlog Queue**: Implemented SQLite table `agent_capability_gaps`, `CapabilityGapRepository`, and Agent Studio "Needs Training" backlog card (`#agentTrainingBacklogCard`) with live count badge and one-click `[⚡ Train in Lab]` or dismissal actions [REQ-FACT-027].
  - **Intelligent Capability Extraction & Direct Chat Queuing**: Enhanced `CapabilityDetector` with `extract_capabilities_from_turn` and `analyze_turn_with_llm` to synthesize technical capability titles, suggested tool names, and starter objectives from user intent and assistant code/commands (e.g. PowerShell `New-VM` / `New-VHD`), eliminating naive retry phrase capture ("can you try again"); streamlined Chat Studio's `[⚡ Train in Lab]` action to queue directly into Agent Studio's "Needs Training" backlog without interrupting modal popups, and fixed backlog list unpacking and rendering in `forge.js` [REQ-FACT-027, REQ-FACT-028].
  - **Operational PowerShell & System Tool Synthesis**: Implemented `ToolSynthesizer` in `src/application/orchestration/tool_synthesizer.py` and integrated into `FactoryRunner` and `promote_factory_job`; dynamically generates real, runnable PowerShell scripts (`tools/<tool>.ps1`) with cmdlets (`Get-VM`, `New-VM`, `Start-VM`, `Stop-VM`, `Restart-VM`, `Checkpoint-VM`, `Remove-VM`, `New-VHD`, `Get-VMSwitch`), Python wrappers with subprocess execution, and runbooks (`SKILL.md`); tests generated tools against the 4-stage verification battery in `_step_sandbox_battery` without dummy code stubs, and mounts the live module dynamically upon promotion [REQ-FACT-009, REQ-FACT-017].
  - **Skill Runbook Feasibility & Parity Audit**: Integrated `evaluate_skill_runbook` into Stage 4 SRE Critic Audit in `VerificationBattery`, strictly validating `agentskills.io` YAML frontmatter (`name`, `description`), structured markdown headers, and 100% action schema parity against synthesized tools before certification.
  - **Instant UI Catalog Sync & Agent Pack Preservation**: Enhanced `promote_factory_job` to merge existing agent metadata, tools, and skills without overwriting custom profiles, sync `SKILL.md` to user skills root, refresh `UserSkillCatalog`, and update in-memory registries and SQLite state store; wired `forge.js` and `app.js` to automatically reload Agent Studio Cards 5 & 6 and Chat Studio dropdowns with zero manual page refreshes.

- CARD-163 Done (`AutoReiv.Data`, `AutoReiv.Infrastructure`, `AutoReiv.Deploy` - CARD-163):
  - **Database Reconciliation & Root Cleanup**: Safely merged 91 older historical sessions and 951 messages from orphaned root `autoreiv.db` into `database/autoreiv.db` (bringing totals to 161 sessions and 1,521 messages) with zero loss of modern settings or custom agents, created a pre-reconciliation zip archive under `backups/`, and cleaned up the obsolete root database and sidecar files.
  - **Enforce database/ Subfolder Invariant in Resolver**: Removed obsolete root path candidate from `_peek_setting_data_dir()` so startup never connects to or touches root SQLite files, and updated `migrate_if_needed()` to automatically reconcile and clean up any legacy root database file detected during bootstrap.
  - **Launcher & Memory Connection Alignment**: Updated Windows launcher (`run_autoreiv.ps1`) to display `database\autoreiv.db` in startup banner, and updated SQLite connection manager fallback to `./data/database/autoreiv.db`.

- CARD-162 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Agents` - CARD-162):
  - **Per-Agent Context Window Control in Agent Studio**: Moved `#forgeContextWindowInput` out of the conditionally hidden provider container into Card 4 ("LLM Provider & Model Override"), making it visible and editable for all agents regardless of whether they use the default provider or a custom provider.
  - **Unrestricted Context Window Persistence**: Updated `forge.js` agent payload builder to parse and persist typed context window tokens for any agent without clearing them when provider is set to "default".
  - **Unified 3-Tier Context Limit Resolution Cascade**: Implemented `resolve_agent_context_limit` in `context_compactor.py` and aligned `agent_kernel.py` and `chat.py` so that token budgets strictly resolve: 1) explicit per-agent setting, 2) per-agent custom model default/overrides, and 3) platform-wide `default_context_window` (e.g. 131,072) from Settings Studio, ensuring chat context meters and execution loops never prematurely truncate to 8k when using default provider.

- CARD-161 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-161):
  - **Chat Options Drawer Context Tokens & Compaction**: Added live token usage badge and progress bar (`#chatContextTokensBadge`, `#chatContextProgressBar`) inside the Chat Options Drawer displaying estimated consumed tokens vs. model context limit (e.g. `2,150 / 32,768 (7%)`), backed by `GET /api/sessions/{session_id}/context`.
  - **Manual Early Session Compaction**: Added `[Compact]` action (`#chatManualCompactBtn`) and `POST /api/sessions/{session_id}/compact` endpoint enabling users to manually compact earlier chat turns into a summary turn before hitting automated context overflow limits, refreshing the chat message stream and token budget immediately.
  - **Active Tools Summary & Inspector Modal**: Added loaded tools badge (`#chatToolsCountBadge`) and `[View Tools]` action (`#chatViewToolsBtn`) opening an interactive modal (`#chatToolsModal`) with live search to inspect all tools and descriptions authorized for the active specialist agent without leaving chat.

- CARD-159 Done (`AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, `AutoReiv.Agents`, `AutoReiv.Web` - CARD-159):
  - **Autonomous Agent Pack Factory & Capability Loop**: Implemented the "Factory in a Lab" architecture for autonomous, overnight creation and training of specialist User Agent Packs with zero breaking changes to existing platform packs.
  - **Core Platform Factory Pack Roster**: Added 5 dedicated factory agent packs under `platform-packs/` (`conductor`, `inspector`, `coder`, `sandbox_runner`, `critic`) hidden from standard chat pickers (`show_in_chat: false`).
  - **Isolated User Pack Authoring Boundary**: Strictly isolated all generated tools, skills, and runbooks within `$DATA_DIR/packs/<agent_id>/`, never polluting platform directories.
  - **Read-Only Environment Inspection & Domain SOP Extraction**: Implemented safe, read-only discovery tools compiling ground-truth `EnvironmentManifest` metadata and domain SOP constraints.
  - **Isolated Sandbox Execution & Mocking**: Extended `EphemeralSandbox` and `SandboxedSubprocessWorker` to support directory mirroring, secret scrubbing, and command stubbing.
  - **4-Stage Automated Verification Battery**: Implemented an exhaustive verification pipeline requiring deterministic execution (Stage 1), safety & path traversal guardrails (Stage 2), idempotency & dirty-state replay (Stage 3), and SRE Critic AST security review (Stage 4).
  - **Conditional Graph Orchestrator & Anti-Bloat Gates**: Built deterministic graph walker with typed SQLite packet interchange (`WorkPacket`, `GapPacket`, `EvalPacket`, `PromotePacket`), anti-bloat `ToolConsolidationGate`, domain `AgentSplitPolicy`, and `UserPackFinalizer`.
  - **Socratic Handshake UX & Promotion UI**: Added "Train Agent" toggle chip, 3-question modal handshake in Chat Studio, and certification promotion card with human-in-the-loop deployment approval.
  - **Universal Attachment Reading Across All Agents**: Authorized `read_document_file` universally in `ScopedToolRegistry` so any agent (platform or custom pack) receiving file attachments in chat can extract and inspect document contents without requiring custom file-reading tools.
  - **End-to-End Hardening & Personal Finance Pack**: Successfully verified the Factory loop end-to-end against a real Personal Finance Agent (`finance`), authoring and certifying 4 atomic domain tools (`log_transactions`, `manage_budget`, `set_savings_goal`, `summarize_finances`) across all 4 battery stages, consolidating tool bloat, and executing live bank transaction ingestion, budgeting, and savings targets with zero database corruption.

## [0.19.0] - 2026-09-05

- CARD-116 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory`, `AutoReiv.Skills` - CARD-116):
  - **First-Class Per-Agent Cognitive Memory Brain**: Implemented private SQLite cognitive memory brain (`$DATA_DIR/packs/<agent_id>/<agent_slug>_memory.db`), strictly separate from domain application database (`<agent_slug>_storage.db`), providing three retrieval shelves: Shelf 1 (Permanent Pinned Directives), Shelf 2 (Rolling Episodic Session Summaries), and Shelf 3 (Atomic Semantic Facts with Porter-stemmed FTS5 BM25 search).
  - **Conflict-Resolved Compilation & Decay Physics**: Compiles facts post-turn without rescanning raw transcripts, performing automated `ADD`, `UPDATE`, `DELETE`, and `BUMP` conflict resolution with mathematical half-life temperature decay and logarithmic access frequency reinforcement.
  - **Dynamic Context Budgeting & Memory Kernel Tools**: Dynamically scales memory token injection according to active model limits (tight <=8k, standard 8k-32k, broad 32k+), and equips memory-enabled agents with `recall_agent_memory` and `memorize_fact` tools.
  - **Autonomous Consolidation Routine**: Implemented background `MemoryConsolidationRoutine` to merge near-duplicates, prune decayed facts past retention days, and compile rolling session summaries without blocking chat turns.
  - **Agent Studio Cognitive Memory Controls & Inspector Drawer**: Added dedicated Cognitive Memory configuration card in Agent Studio with retention range slider (`#forgeMemoryRetentionDays`), pinned directives editor (`#forgePinnedMemory`), and an interactive Brain Inspector drawer (`#agentBrainDrawer`) with FTS5 search, individual fact forgetting (`DELETE /api/agents/{id}/memory/facts/{fact_id}`), and complete memory purge actions.

- CARD-148 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory` - CARD-148):
  - **Per-Agent Persistent Storage in Agent Studio**: Added Persistent Storage checkbox (`#forgeStorageEnabled`) and Database Type selector (`#forgeStorageType`) to Agent Studio roster sheet, allowing specialist agents to maintain dedicated private databases.
  - **Pack-Scoped Storage & Artifact Layout**: Placed agent persistent storage databases (`<agent_slug>_storage.db`) and recipes (`workflows/`) directly inside that agent's pack directory (`$DATA_DIR/packs/<agent_id>/`), eagerly creating the database upon save so the agent's files stay together throughout their lifecycle.
  - **Dedicated Central Database Directory**: Relocated central system SQLite database from the root of `$DATA_DIR` into `$DATA_DIR/database/autoreiv.db`, with automatic on-boot migration of existing `autoreiv.db`, `-wal`, and `-shm` files.
  - **Auto-Authorized Storage Platform Tools**: Added `query_agent_database` (read queries) and `execute_agent_database` (DDL & mutations) tools in `src/application/skills/agent_storage_tools.py`, automatically authorized for storage-enabled agents during execution turns.
  - **Agent Pack SDK Storage Support**: Extended `AgentPackManifest` (`pack.json`) and `AgentPackService` to preserve storage configuration during agent pack export, import, and scaffolding.

- CARD-157 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-157):
  - **Host Command Auto-Delegation**: Updated Assistant platform pack system prompt to immediately delegate host terminal, CLI, PowerShell, and network diagnostic commands (e.g. `ipconfig`, `ping`) to the `AutoReiv` platform agent via `handoff_to_agent(target_agent='autoreiv')`.
  - **Subagent-Aware Pending Approvals**: Updated `/api/approvals/pending` and SQLite approvals repository to return pending approvals for the active session and all its child and phase execution branches (`session_id = ? OR session_id LIKE ? || '_child_%' OR session_id LIKE ? || '::phase::%'`), ensuring subagent approval cards are not hidden when querying from the parent chat session.
  - **Chained Nested HITL Flow**: Updated `shouldResumeChatAfterHitl` and Chat Studio approval handlers to detect intermediate subagent approvals (`nested.status === 'approval_required'`), rendering the next pending approval card rather than prematurely resuming the parent assistant turn.
  - **Chat Bubble Lifecycle & Streaming Indicator Cleanup**: Removed premature `loadMessages` call at turn start to prevent wiping the user prompt bubble and flashing the empty conversation placeholder, and ensured the pulsing `Streaming...` badge is cleanly removed upon completion, stop, or HITL approval pause.

- CARD-151 Done (`AutoReiv.Web`, `AutoReiv.Chat` - CARD-151):
  - **Grey Out HITL Action Buttons Upon Decision**: Added immediate disabled visual feedback (`disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none`) to Human-In-The-Loop approval cards in Chat Studio and plan review milestones.
  - **Persistent Resolved Styling**: Permanently strips bright emerald/rose background colors upon approval or rejection, replacing them with neutral slate styling (`bg-slate-800 text-slate-500 border border-slate-700/60 cursor-not-allowed opacity-50`) to clearly indicate the decision is finalized and prevent accidental duplicate clicks.
  - **Pre-Resolved Card Rendering**: Added pre-resolved disabled rendering in `buildHitlCardInnerHtml` for cards rendered from history with existing decisions.

- CARD-150 Done (`AutoReiv.Web`, `AutoReiv.Chat` - CARD-150):
  - **Chat Session Summaries & Compact Timestamp Badges in History Drawer**: Replaced generic "Assistant Chat" list items in the past conversations drawer with a compact 2-line stacked card showing a clean 2–5 word topic title and a shorthand timestamp (e.g. `Sep 03, 11:50 AM`).
  - **Turn-1 Automatic Title Summarization**: Automatically extracts a clean 2–5 word topic summary from the user's initial turn prompt and persists it to the SQLite `sessions` table, replacing generic default titles.
  - **Session Title Update Endpoint**: Added `PATCH /api/sessions/{session_id}` endpoint to support programmatic session title updates and manual rename actions.
  - **Session Timestamp Formatter**: Added `formatSessionTimestamp` in pure frontend formatters converting UTC ISO timestamps to local `MMM DD, h:mm A` format.

- CARD-154 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Chat` - CARD-154):
  - **Shield Background Workers from Mobile Client Disconnects**: Prevented client-side SSE disconnects (mobile phone sleep, tab lock, or app switching) from canceling background worker execution tasks, ensuring subagent handoffs run to completion and persist final responses.
  - **Session Status Endpoint**: Added `GET /api/sessions/{session_id}/status` returning whether a session has an active background task or job in flight and the ID of the active agent.
  - **Tab Sleep Wakeup & Background Polling Recovery**: Updated `chat.js` visibility and window focus listeners to check session status on wake-up; if background work completed while away, streaming UI state automatically resets and loads all persisted messages from SQLite; if work is still underway, it polls and smoothly recovers upon completion.
  - **Preserved Explicit User Abort**: Preserved explicit user cancellation via `POST /api/chat/stream/{session_id}/abort` when the Stop button is clicked.

- CARD-156 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings` - CARD-156):
  - **Per-Agent LLM Endpoint Credentials & Configuration**: Added expandable endpoint controls in Agent Studio (API Base URL, API Key/Token, and Context Window tokens) revealed whenever an agent's LLM Provider is set to a specific provider.
  - **Live Model Discovery in Agent Studio**: Added `[ 🔄 Refresh Models ]` button in Agent Studio that queries live models from the configured endpoint and dynamically populates the Model selector.
  - **Clean Collapsed Default**: When set to "Use Global Default", per-agent endpoint controls remain hidden and inherit settings directly from Settings Studio.
  - **Persistence & Kernel Dispatch**: Persisted `api_base_url`, `api_key`, and `context_window` in SQLite `custom_agents` and `agent_overrides` tables and updated `AgentKernel` to route agent generation through custom endpoint adapters and respect agent context token limits.

- CARD-153 Done (`AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Settings` - CARD-153):
  - **Per-Agent LLM Provider and Model Configuration**: Replaced the abstract Purpose Matrix with direct LLM Provider and Model dropdowns on the Agent Studio roster sheet, defaulting to "Use Global Default".
  - **Purpose Matrix Retirement**: Completely removed the Purpose-Based Model Routing grid from Settings Studio and deprecated the `ModelPurpose` enum, simplifying model configuration into a single, direct path.
  - **Streamlined Resolution Cascade**: Simplified `AgentKernel._resolve_model()` cascade: agent override (`provider`/`model`) -> global default from Settings -> gateway fallback, eliminating matrix lookups.
  - **Agent Pack Schema & Persistence**: Added `provider` field to `AgentProfile`, `AgentCustomization`, and `AgentPackManifest` schema, persisting per-agent provider choices across restarts, exports, and imports.

## [0.18.0] - 2026-09-03

- CARD-152 Done (`AutoReiv.Web`, `AutoReiv.Memory` - CARD-152):
  - **Prompts Studio (Dedicated Prompt Management Space)**: Added a dedicated, first-class Prompts Studio (`#promptsStudio`, `#view-prompts`) in the main sidebar navigation with an ergonomic dual-pane management interface.
  - **Dual-Pane Prompt Workspace**: Left pane provides live search, category filter pills (All, System, Productivity, Coding, Analysis), and prompt cards with built-in badges; right pane provides a full-height template editor with tags, category selection, and instant `[ Test in Chat ]` workflow.
  - **Lightweight Chat Quick-Picker**: Streamlined the Chat Studio options drawer by replacing the large modal with a fast, non-intrusive Quick Prompt popover dropdown (`#chatPromptsQuickPicker`) for 1-tap template insertion and a direct bridge to Prompts Studio.

- CARD-147 Done (`AutoReiv.Web`, `AutoReiv.Memory` - CARD-147):
  - **Prompt Catalog & Saved Prompts Manager**: Delivered an end-to-end prompt template management system with instant 1-click insertion into the Chat Studio input dock.
  - **SQLite Prompt Catalog Repository & Schema**: Implemented `prompt_catalog` schema, migrations, and `PromptRepositoryMixin` with full CRUD support and curated built-in system, productivity, coding, and analysis seed templates.
  - **REST API Endpoints**: Added `GET /api/prompts`, `POST /api/prompts`, `PUT /api/prompts/{id}`, and `DELETE /api/prompts/{id}` with search and category filtering.
  - **Interactive Drawer Trigger & Modal**: Activated `#chatPromptsBtn` in `#chatOptionsDrawer` opening `#promptCatalogModal` with search, category tabs (System, Productivity, Coding, Analysis), card previews, inline create/edit form, and 1-click **Insert into Chat** action.

- CARD-145 Done (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-145):
  - **Comprehensive Document Extraction Pipeline**: Added universal document parsing tools to extract text, tables, and structures from PDFs (`.pdf`), Excel spreadsheets (`.xlsx`, `.xls`), Word documents (`.docx`), CSVs (`.csv`), and code/text files.
  - **Specialist Agent Tool (`read_document_file`)**: Registered `read_document_file(path, max_pages, max_rows)` tool in `DocumentTools` accessible to both `assistant` and `autoreiv` platform agents.
  - **Automatic Turn-1 Previews**: Enhanced chat prompt formatting so attached small documents and spreadsheets (< 16 KB) automatically inline parsed table grids and section summaries directly into the initial turn prompt.

- CARD-144 Done (`AutoReiv.Gateway`, `AutoReiv.Web` - CARD-144):
  - **Native Multimodal Image Vision Gateway**: Extended LLM provider adapters (`OpenAIProviderAdapter`, `OllamaProviderAdapter`) and `ChatMessage` domain models to support native vision image input payloads.
  - **OpenAI & Gemini Multimodal Formatting**: Serializes attached images and local path references into OpenAI-standard `{"type": "image_url", "image_url": {"url": "data:image/...;base64,..."}}` content structures for vision-capable models (e.g. Gemini 1.5/2.0 Flash, GPT-4o).
  - **Ollama Vision Support**: Automatically extracts and packages Base64 image byte strings into Ollama's native `images: [...]` payload for local Vision-Language Models (e.g. `qwen2.5-vl`, `llava`).
  - **Zero-Migration Backward Compatibility**: Automatically detects and extracts local image paths referenced in prompt annotations without database schema alterations.

- CARD-143 Done (`AutoReiv.Web` - CARD-143):
  - **Chat Media & File Attachments Pipeline**: Introduced backend and frontend infrastructure allowing users to attach images, videos, audio, PDFs, code, and text files directly to chat sessions.
  - **Secure Ingestion & Serving Endpoints**: Built `POST /api/chat/upload` with path traversal sanitization and safe session directory sandboxing, and `GET /api/chat/attachments/{file_id}/{filename}` for streaming files with accurate MIME types.
  - **Interactive Attachment Staging Bar**: Activated `#chatAttachBtn` in the options drawer to open device file pickers; added `#chatAttachmentsPreviewList` inside the input form rendering file thumbnails, names, formatted sizes, and 1-click removal buttons before dispatch.
  - **Message Thread Previews**: Updated user message rendering in the chat thread to display media attachment grids and download pills.

- CARD-142 Done (`AutoReiv.Web` - CARD-142):
  - **Collapsible Chat Actions Drawer**: Replaced the cluttered mode checkboxes and dropdown that permanently occupied 2+ rows in the input dock with an ergonomic **`[ + ]` Action Button** (`#chatOptionsToggleBtn`) and expandable drawer (`#chatOptionsDrawer`), reclaiming 50px+ of vertical chat space on mobile.
  - **Options Popout Sheet**: Built an accessible, animated popout tray featuring runtime mode toggles (Verify, Goal Mode, Auto-run), the workflow selector, and reserved slots for upcoming media attachments and prompt catalog tools.
  - **Active Modes Indicator**: Added `#chatActiveModesIndicator` displaying real-time badges (e.g. `🎯 Multi-phase job`, `Auto-run`, `Verify Active`) adjacent to the options trigger button so active modes are immediately visible even when the drawer is tucked away.
  - **Keyboard & Click-Away Dismissal**: Supports pressing `Escape` or tapping anywhere outside the drawer to dismiss it naturally.

- CARD-141 Done (`AutoReiv.Web` - CARD-141):
  - **Wiki Note Responsive Header**: Redesigned `#wikiNoteHeader` to stack comfortably on mobile (`flex-col sm:flex-row`), guaranteeing full-width breathing room for note titles (`#activeWikiTitle`) and relative path pills (`#activeWikiPath`) without truncating behind action controls.
  - **Collapsible YAML Frontmatter Inspector**: Replaced the bulky static metadata box with a slim 28px summary bar (`#wikiFmSummaryBar`) and quick toggle button (`#wikiToggleFmBtn`), reclaiming massive vertical space for note reading and editing.
  - **Rendered vs. Raw YAML Toggle**: Built a segmented view mode switcher inside the expanded frontmatter card, allowing users to toggle between visual pills/tags/summaries (`#fmRenderedView`) and exact monospace YAML syntax (`#fmRawView`) with a 1-click clipboard copy button (`#fmCopyRawBtn`).
  - **Backend Raw Frontmatter Extraction**: Enhanced `read_note` in `WikiStore` and `FrontmatterParser` to extract and return exact `raw_frontmatter` strings in note REST payloads.

- CARD-140 Done (`AutoReiv.Web` - CARD-140):
  - **Removed Obsolete Wiki Knowledge Graph Modal and Button**: Deleted the non-interactive Mermaid-based Graph modal (`#wikiGraphModal`) and its toolbar button (`#wikiGraphViewBtn`), uncluttering the Wiki Studio toolbar and focusing users on the interactive Force-Directed Mind Map (`#wikiMindMapModal`).

- CARD-139 Done (`AutoReiv.Web` - CARD-139):
  - **Three-Surface Information Architecture**: Replaced the cluttered 7-page navigation with 3 consolidated core surfaces: **Cockpit** (Chat Studio & Workbench), **Vault** (Wiki & Projects), and **Fleet** (Agents, Routines, Observability, Settings).
  - **Mobile Header Surface Switcher**: Added `#mobileSurfaceSwitcher` with quick pills for `#surfaceBtnCockpit`, `#surfaceBtnVault`, and `#surfaceBtnFleet`.
  - **Streamlined Conversations Drawer**: Redesigned `#sidebar` so that **+ New Conversation** and the full **Conversations List** (`#sessionList`) take 85% of the drawer, moving the 7 studios to a compact 2-column footer strip (`#sidebarNav`) while preserving all ARIA contracts.
  - **Desktop Default-Collapsed Sessions**: Configured `#sidebar` to default to collapsed on desktop, maximizing chat space while remaining instantly accessible via the session toggle button.

- CARD-138 Done (`AutoReiv.Web` - CARD-138):
  - **52px Slim Icon Rail**: Replaced permanent 280px left sidebar with a sleek, responsive desktop rail (`#appRail`) and toggleable sessions drawer (`#toggleSidebarBtn`), reclaiming over 220px of desktop horizontal space.
  - **Dual-Pane Workbench Canvas**: Built `#chatWorkbenchPane` that renders artifacts (markdown plans, code snippets, diffs) side-by-side with conversation on desktop ($> 1024\text{px}$) and as an intuitive full-height slide-out sheet on mobile ($< 1024\text{px}$).
  - **Artifact Interaction Controls**: Added tabbed preview/raw views (`#workbenchTabPreview`, `#workbenchTabRaw`), one-click clipboard copy (`#workbenchCopyBtn`), and save-to-wiki (`#workbenchSaveWikiBtn`).
  - **Message Artifact Integration**: Inlined `.workbench-msg-btn` in agent message bubbles for seamless one-click artifact inspection.

- CARD-137 Done (`AutoReiv.Web` - CARD-137):
  - **Modern Systematic UI Overhaul**: Implemented concentric corner radius system (`inner = outer - padding`), edge-touching zero-radius rules, size-following hierarchy, and focus ring offsets across AutoReiv's frontend.
  - **Unified Ergonomic Chat Input Card**: Replaced stacked two-row input bar with an integrated floating card container, reclaiming 40px+ of vertical chat space while preserving 100% of mode toggles, status pills, and action controls.
  - **Maximized Chat Workspace**: Expanded message container from `max-w-2xl` to `max-w-4xl` for spacious multi-agent reasoning, rich code blocks, and markdown tables.
  - **Refined Control Center & Drawers**: Upgraded top bar action group and applied concentric nested radii to the Journey Drawer and Debug Inspector.

- CARD-136 Done (`AutoReiv.Web`, `AutoReiv.Observability` - CARD-136):
  - **Per-Chat Debug Inspector**: Created slide-over inspector `#chatDebugPane` with button `#chatDebugToggleBtn` in Chat Studio.
  - **Diagnostic Envelopes Endpoint**: Added `GET /api/chat/sessions/{session_id}/debug` returning raw LLM message lists, tool call parameters, latency breakdown, TTFT, token usage, and system prompt.
  - **Multi-Tab Payload Viewer**: Integrated tabbed view for Messages, Tool Executions, Metrics, and System Prompt with one-click JSON clipboard copy.

- CARD-135 Done (`AutoReiv.Web`, `AutoReiv.Orchestration`, `AutoReiv.Memory` - CARD-135):
  - **Execution Journey Timeline**: Created slide-out inspector `#chatJourneyDrawer` with action button `#chatShowJourneyBtn` in Chat Studio.
  - **Journey Synthesis Endpoint**: Added `GET /api/chat/sessions/{session_id}/journey` aggregating active multi-phase jobs, chronological milestones, tool execution spans with duration, and session artifacts.
  - **Interactive Milestones & Artifacts**: Visual vertical timeline with status badges (queued, running, done, failed) and key discoveries list.

- CARD-134 Done (`AutoReiv.AgentPacks`, `AutoReiv.Web` - CARD-134):
  - **Control Plane Focus & Dashboard Retirement**: Cleanly retired experimental dynamic dashboard renderer and custom pack UI tabs to preserve AutoReiv's core focus as a high-performance Multi-Agent Control Plane.
  - **Stream Cancellation & Engine Delegation**: Implemented true task abort on `POST /api/chat/stream/{session_id}/abort` with `#stopBtn` UI control; delegated `dispatch_handoff` to `HandoffIsolationEngine`.
  - **Episodic Full-Text Search**: Added native SQLite FTS5 virtual table `episodic_facts_fts` with BM25 ranking and automatic triggers for memory retrieval.

- CARD-133 Done (`AutoReiv.AgentPacks`, `AutoReiv.Web` - CARD-133):
  - **Declarative Dashboard Schema**: Created `AgentDashboardManifest` and `DashboardCardDefinition` models supporting `stat_group`, `action_group`, `data_table`, `markdown_editor`, and `markdown_viewer` card types.
  - **AutoReiv Platform Authoring Tools**: Added `scaffold_agent_dashboard` and `read_agent_dashboard` tools to the `build-agent-pack` skill, enabling AutoReiv to generate rich custom dashboards via natural language in Chat.
  - **Dashboard REST API**: Added `GET /api/agent-packs/dashboards`, `GET /api/agent-packs/{pack_id}/dashboard`, `POST /api/agent-packs/{pack_id}/dashboard`, and `POST /api/agent-packs/{pack_id}/action` with ScopedToolRegistry RBAC verification.
  - **Dynamic Studio Frontend Renderer**: Implemented `dynamic_studio.js` module dynamically mounting custom specialist studio tabs into the sidebar navigation, rendering interactive KPI stats, action buttons with loading spinners and toasts, data tables with row actions, and markdown editors.
  - **Gardening Specialist Starter Pack**: Seeded `agent-packs/gardening/` starter pack with `pack.json`, `SKILL.md`, `dashboard.json`, and sample `docs/garden_journal.md`.

- CARD-132 Done (`AutoReiv.Agents`, `AutoReiv.Web` - CARD-132):
  - **Cascading Custom Agent Cleanup**: Standardized custom agent deletion to always cleanly unbind assigned routines, delete operator overrides, and remove physical pack folders from disk.
  - **Permanent Telemetry Purge Toggle**: Added `purge_history` query option and Agent Studio confirmation modal (`#deleteAgentModal`) allowing operators to toggle permanent historical purge of session messages and telemetry records upon agent deletion.

- CARD-131 Done (`AutoReiv.Agents`, `AutoReiv.Web` - CARD-131):
  - **Dynamic Tone Registry**: Created `ToneDefinition` model and SQLite table `tones` seeded with 6 built-in presets (*default, technical, concise, friendly, academic, socratic*) and supporting durable custom tones.
  - **Tone REST API**: Implemented `/api/tones` endpoints for listing, creating, updating, and deleting custom tone directives with built-in protection.
  - **Agent Studio Manage Tones Modal**: Added `[ ⚙️ Manage Tones ]` button to Card 3 in Agent Studio opening a rich management modal (`#manageTonesModal`) with live list, create form, inline editing, and deletion.
  - **Dynamic System Prompt Injection**: Updated `AgentProfile.get_effective_system_prompt()` and `AgentKernel` to dynamically resolve custom tone directives from database when assembling system prompts.

- CARD-130 Done (`AutoReiv.Observability`, `AutoReiv.Web` - CARD-130):
  - **Agent Studio Lifetime Telemetry**: Bound `loadAgentTelemetry(agentId)` to parse per-agent breakdown metrics from `data.agents` with legacy ID alias resolution, fixing the 0-stat blank display.
  - **Per-Agent Estimated Cost ($)**: Added `estimated_cost_usd` to `AgentKPISummary` and added a dedicated **Est. Cost ($)** badge in Agent Studio under *Agent Telemetry & Lifetime Stats*.
  - **Observability Studio Cost & TTFT Surfacing**: Added **Est. Cost ($)** and **Avg TTFT (ms)** cards to the top KPI overview row, and added an **Est. Cost ($)** column to the *Per-Agent KPI Breakdown* table.

## [0.17.0] - 2026-08-31

- CARD-129 Done (live-test pass) (`AutoReiv.Observability`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-129):
  - **Distributed Hierarchical Tracing**: Extended `TelemetrySpan` and SQLite `telemetry_spans` table with `trace_id` and `parent_span_id` columns, propagating trace context across turns, tool calls, and subagent handoffs.
  - **Provider & Model Attribution**: Added indexed `provider` and `model` columns on telemetry spans for side-by-side performance comparisons across Ollama, Gemini, Claude, and OpenAI.
  - **Time-To-First-Token (TTFT)**: Captured streaming latency `ttft_ms` across gateway adapters and exposed `avg_ttft_ms` in `KPIDashboardSummary`.
  - **HITL Safety Classification**: Fixed intentional Human-in-the-Loop safety pauses (`approval_required`) to record as `status="hitl_paused"` (`success=True`), eliminating false-positive error spikes.
  - **Cost & KPI Modernization**: Added real-time token cost estimation (`estimated_cost_usd`) and `hitl_paused_count` to KPI dashboard aggregations.
  - **Database Evolution**: Added automatic lightweight schema migrations in `connection.py` preserving existing SQLite databases with zero data loss.
  - **Delegation & Parameter Resilience**: Added automatic type coercion to `HandoffPacket` and tool argument aliasing across orchestration and wiki tools.

- CARD-125 Done (live-test pass) (`AutoReiv.Wiki`, `AutoReiv.Skills` - CARD-125):
  - Deterministic 27-key YAML front matter sequence serialization (`uid`, `title`, `aliases`, `document_type`, `domain`, `topic`, `tags`, `summary`, `status`, `priority`, `sensitivity`, `confidence_score`, `pinned`, `parent`, `related`, `moc`, `source`, `author`, `model`, `content_hash`, `date_created`, `last_updated`, `last_accessed`, `access_count`, `word_count`, `context_tokens`, `schema_version`).
  - Added 16-character SHA-256 `content_hash` computation on notes and tracking for `author`, `model`, `source`, `pinned`, and `access_count`.
  - Enforced strict 2-depth limit under `notes/<domain>/<topic>/<slug>.md` and standard `operations/worklog` / `operations/diagnostics` for routine and weekly logs.
  - Added atomic `wiki_note_append` tool and enhanced `wiki_note_list` with status, tag, author, pinned, and priority metadata filtering.
  - Added incoming `backlinks` calculation on note reads.
  - Authoritative Platform skill runbook in `src/infrastructure/skills/seeds/wiki/SKILL.md` and `platform-packs/assistant/skills/wiki/SKILL.md`.
  - Cleaned vault root folders: removed misplaced templates from `notes/`, relocated weekly logs to `notes/operations/worklog/`, removed legacy directories, and seeded single canonical template at `resources/templates/note_template.md`.

## [0.16.0] - 2026-08-31

- CARD-128 Done (live-test pass) (`AutoReiv.Gateway`, `AutoReiv.Settings` - CARD-128):
  - Added dedicated presets and gateway support for 10 LLM providers: **Ollama (Local)**, **LM Studio (Local)**, **vLLM (Self-Hosted)**, **Google Gemini**, **OpenAI**, **Anthropic Claude**, **OpenRouter**, **Groq Cloud**, **DeepSeek**, and **Together AI**.
  - Built `AnthropicProviderAdapter` (`src/infrastructure/gateway/anthropic_adapter.py`) supporting direct Anthropic Messages API (`/v1/messages`) with `x-api-key`, message/tool translation, and streaming SSE events.
  - Hardened `OpenAIProviderAdapter` to capture reasoning tokens (`reasoning_content` / `reasoning`), robust tool call parsing, Gemini thought signature preservation, guaranteed tool message name resolution, and standard `/v1/models` discovery.
  - Implemented automatic per-provider `HTTP 429` rate limit backoff retry loops with intelligent `retryDelay` and `Retry-After` parsing across OpenAI and Anthropic adapters.
  - Updated Settings Studio dropdown and defaults in `index.html` and `settings.js` for 1-click provider switching.


## [0.15.0] - 2026-08-31

- CARD-127 Done (live-test pass; Jacob approved layout) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-127):
  - Agent Studio top-down hierarchy: Top box is "Platform Skills & Tools" (shared capabilities: `wiki`, `coordination`, `proposals`, `worker`, `planning`, `verification`, `sdlc-cards`, `sandbox`), bottom box is "[Agent Name] Pack Skills & Tools" (dedicated pack skills).
  - Completely removed "Also ticked" / `ungrouped_pack_tools` floating checkbox rendering. Every single tool is nested under a parent skill accordion.
  - Promoted cross-assigned / shared tools into first-class Platform skills (`coordination`, `proposals`, `worker`, etc.) with full metadata and nested tool toggles.
  - Updated `platform-packs/assistant` (dedicated `weekly-tasks`) and `platform-packs/autoreiv` (dedicated `build-agent-pack`, `platform-health`, `session-inspect`) to receive shared permissions from Platform skills without orphan tools.
- CARD-126 Done (live-test pass) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-126):
  - Three homes: Platform skills/tools, Platform Agent Packs (`platform-packs/assistant` + `autoreiv`, always seed-if-missing into `$DATA_DIR/packs/`), user packs (`agent-packs/` still not scanned on startup). Dropped Python builtins for Assistant and AutoReiv; Agent Builder stays hidden. Platform skill `wiki` stub with nested wiki tools. Assistant pack owns `weekly-tasks`; AutoReiv owns `build-agent-pack` / `platform-health` / `session-inspect`. Agent Studio nests tools under skills (Platform box, then this pack). Chat still lists ticked tool schemas every turn (CARD-117/121).
- CARD-124 Done (live-test pass) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-124):
  - Shipped core is Assistant + AutoReiv (Agent Builder stays a hidden builtin). Conductor, Coding, and Review are three Agent Packs in `agent-packs/` (optional import, not auto-loaded on startup). Chat shows Conductor; Coding/Review stay handoff-only. Review ticks `git_diff` / `git_status` and never write/commit. Jacob's `$DATA_DIR/packs/` imported on this card.
- CARD-125 Ready (later backlog, not this pickup) (`.github/cards/` - CARD-125):
  - Revisit Wiki schema, tools, and operating manual. Emphasis: correct deterministic YAML front matter and extensive metadata. Platform skill `wiki` stub is the Studio/packs squeeze-in; this card is the later fill. Do not implement until Jacob says build.
- CARD-119 Done (live-test pass; Jacob said look good) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - Agent Packs are packaging of one specialist (nested skills/tools schema 1.1, Agent Studio Import/Export, New Agent hands off to AutoReiv in Chat). AutoReiv skills: build-agent-pack (scaffold/import/export) and recommend-capability (HITL propose when stuck). Agent Builder hidden from Chat and Agent Studio list. Show in Chat default on. Foo pack create + delete worked. Local commit only. No push.
- CARD-119 hide Agent Builder from Chat picker (`AutoReiv.Web` - CARD-119): skip `agent-builder` by id in Chat pickers; API serializes `show_in_chat=false` so a stale override cannot turn it back on. Status Done (live-test pass). Local commit only. No push.
- CARD-119 AutoReiv pack vs recommend skills; hide Agent Builder (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - AutoReiv skills are `build-agent-pack` (scaffold/import/export a named specialist) and `recommend-capability` (HITL propose_* when there is no path). `save_agent_specification` is not ticked on AutoReiv; pack write is `scaffold_agent_pack`. Agent Builder is hidden from Chat (`show_in_chat=false`) and skipped in the Agent Studio left list; API/handoff may still resolve the id. Coding / Conductor / Review stay. No named observability skill. Status Done (live-test pass). Local commit only. No push.
- CARD-119 follow-up New Agent AutoReiv handoff and nested pack skills (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - New Agent in Agent Studio switches to Chat, selects AutoReiv, starts a fresh session, and fills `I am ready to create a new agent.` (focused, not auto-sent). Nested pack schema 1.1 puts tools under skills; `allowed_skill` / `pack_tool_names` stay derived compat. AutoReiv `build-agent-pack` asks for agent details, each skill, and tools per skill. Status Done (live-test pass). Local commit only. No push.
- CARD-119 Agent Packs import/export/build (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-119):
  - Product landed. Agent Pack is packaging, not a fourth primitive: schema + how-to (`docs/agent-packs.md`), Agent Studio Import/Export on the selected agent, `show_in_chat` (default on) persisted and filtered in Chat pickers only, pack-owned tool ids fill the Pack-owned group and come on with the pack, AutoReiv runbook `build-agent-pack` plus `export_agent_pack` / `import_agent_pack` / `scaffold_agent_pack`. Workflows ride along; transcripts, secrets, and instance facts do not. Builtins not ripped. okta-admin not reshipped. No Pack Studio. Status Done (live-test pass). Local commit only. No push.

- CARD-123 Done (live-test pass; Jacob said it feels great) (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-123):
  - Workflow is a reusable plan on the agent who starts it (JSON under `$DATA_DIR/agents/<id>/workflows/`). Goal remains the one-off factory. After a Goal-planned job: Save as workflow stores the chapter list (who, skill vs handoff, done-when), not instance facts. Chat picker next to Goal and Verify is empty until the first save. Pick a recipe + new prompt instantiates a Job with those Phase rows. Agent Studio has a small owned-recipes list (edit name/order/who/skill-vs-handoff, delete with confirm). No Workflow Studio. No Agent Packs (119), no memory (116). CARD-118 marked Done (live-test pass). Pickup later is CARD-119 or CARD-116 when Jacob asks.

- CARD-118 one Agent Studio; drop Skills Studio and Forge place name (`AutoReiv.Web` - CARD-118):
  - One screen: Agent Studio. Skills Studio removed from the main nav and page. Selected agent shows identity, instructions, tone, Tools (CARD-121 checklists), and Skills runbooks (CARD-117 ticks plus open/edit of SKILL.md name, blurb, and body). Archive/confirm-delete of user runbooks moved here. Users do not hand-edit Python tool implementations. Retire Forge as a place name (h2/copy/app init). `forge.js` filename and element ids kept. Stop shipping `okta-admin` as a bundled seed: removed repo seed `src/infrastructure/skills/seeds/okta-admin` and the live data-dir copy only (`%LOCALAPPDATA%\\AutoReiv\\skills\\okta-admin`). No mass-delete of other user skills. APIs for list/read/write SKILL.md kept. No Agent Packs (119), no Workflow Studio (123), no memory (116). CARD-120 marked Done (live-test pass). Status In Review.

- CARD-120 Done (live-test pass; Jacob said ok next) (`AutoReiv.Kernel` - CARD-120):
  - Rename-only accepted. Skill in code means SKILL.md runbook. Pickup is CARD-118.

- CARD-120 rename Python tool groups so skill means runbook (`AutoReiv.Kernel` - CARD-120):
  - Tool-group modules/classes renamed `*Skill` → `*Tools` (`wiki_tools.py` / `WikiTools`, `git_tools.py` / `GitTools`, `card_tools.py` / `CardTools`, sandbox `execute_code` wrappers, etc.). Folder `src/application/skills/` kept: runbook catalog (`user_catalog`, `dynamic_loader`, `skill_curator`) stays; tool-group files are no longer `*_skill.py`. Manifest clustering identifiers no longer call tool groups skills. Zero behavior change. Tool callable names, `allowed_skill`, and `skill_view` unchanged. CARD-121 marked Done (live-test pass).

- CARD-121 tools as one callable and two Studio groups (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-121):
  - Done (live-test pass). Tool = one atomic callable. Agent Studio tools card is Pack-owned (empty until Agent Packs) and Platform checkboxes. Dropped pack-master / skill-pack grouping and RBAC copy. Untick still omits schema. SKILL.md JSON stubs stay labels, not model callables. Wiki stays split (`wiki_note_read` / `wiki_note_create` / ...). Builtin allowlists unchanged. CARD-117 marked Done.

- CARD-117 skill allowlist and name+blurb prompt inject (`AutoReiv.Web`, `AutoReiv.Kernel` - CARD-117):
  - `AgentProfile.allowed_skill` persists via the agents API (and across reload). Prompt injects this agent's ticked SKILL.md names + short descriptions, not the runbook body. `skill_view` refuses unticked ids. Empty allowlist injects nothing. Platform skills default off (no silent okta-admin). Pack-owned group is empty until Agent Packs. Agent Studio checklist next to the existing tool checkboxes.

- CARD-123 walked save Goal plan as workflow, picker in Chat (`.github/cards/` - CARD-123):
  - Walked lock recorded, not built (Jacob t161-t164u). Workflow = reusable plan. Lives with the agent who starts it. Picker in Chat next to Goal and Verify, only that agent's startable recipes. Do not force workflows day one; empty picker is correct. Primary birth: Goal checkbox then Chat 'Save as workflow' after a plan/run you like. New prompt + picked workflow = new Job, same chapters, different facts. Goal is the factory, not already a workflow. Goal plans phases today; there is no save and no picker. Start in Chat; optional later edit in Agent Studio on the owner. No Workflow Studio. One object: a phase is skill or handoff. Save the chapter list, not instance facts. Pickup after CARD-117 / CARD-121 / CARD-120. Skills Studio is not the house (CARD-118). Status stays Ready. No product code.

- CARD-118 walked one Agent Studio; drop Skills Studio and okta-admin seed (`.github/cards/` - CARD-118):
  - Walked lock recorded, not built (Jacob t159-t160u). Drop Skills Studio as a standalone pack editor (not freeze-as-the-destination). A skill belongs to an agent. One screen: Agent Studio. Sidebar already says Agent Studio; app.js/h2 still say Agent Forge / Agent Forge Studio — retire Forge as a place name. Checkbox grid is the Tools section, not a second product. Selected agent: instructions, tone, platform ticks (All Off except Assistant/AutoReiv), pack skill list (open/edit runbooks), pack tool ticks. Users do not hand-edit tool implementations; pack-builder / Agent Builder later owns wiring tools. Fewer pages. Later CARD-119 Agent Packs = import/export/backup of the same agent in user data on this screen, not a third pack-manager tab unless the list gets huge. Drop shipped `okta-admin` seed as a product pack (teaching example, not a specialist). Do not delete files here; seed lives `src/infrastructure/skills/seeds/okta-admin` and `$DATA_DIR/skills/okta-admin`. CARD-108 was the seed; this card owns do-not-keep-as-product-pack. Core roster still Assistant + AutoReiv (CARD-119). Status stays Ready. No product code.

- Opened backlog CARD-123 Workflow recipe (`.github/cards/` - CARD-123):
  - Alignment only. Workflow is a first-class recipe. Not a skill. Not Goal. Instantiating creates a Job with Phase rows. Lives next to jobs, not in Skills Studio. Agent Studio / later a section, not a new graph runtime. Pickup after CARD-117 / CARD-121 / CARD-120. Cheat-sheet lock: workflow (recipe) vs job (this run) vs phase (chapter). HR new-employee-onboarding example without requiring live HR. Change list stub: object is missing today; Goal checkbox is a one-off planner; every chat is a Job named Chat. Status Ready. `type:docs` `type:refactor`. No product code.

- Artifact naming scrub 2026-08-30 t157u (cards, specs, CHANGELOG, ADRs, RTM, user-visible strings):
  - Inspiration product names removed from AutoReiv artifacts unless we are literally integrating that product. CARD-116 may still name Mem0/Letta/Zep as a vendor evaluation. Research folder outside this repo may keep names. Reworded to: user data outside git; progressive disclosure (name+blurb then body); skill curator archive; purpose-based model routing; child session gets the packet only; prior art studied outside this repo. Do not point this repo at a research path for inspiration products. No product code.

- CARD-121 walked change list 2026-08-30 (`.github/cards/` - CARD-121):
  - Walked lock recorded, not built. Tool = one callable. Split read vs write where it matters (`wiki_read` / `wiki_write`). Agent Studio two groups: pack-owned ON with the agent; platform All Off except Assistant and AutoReiv. Untick omits schema (already true via `allowed_tool_names`; keep it true). Do not put stub JSON tools from SKILL.md into the model as callables. Do not hide real tools inside a skill. Drop/rename Forge pack-master grouping so it does not say skill pack. `manifest.py` clustering tools into skill packs is the wrong mix. No live Okta, no mapper, no 12-tool warning (CARD-115 already removed it). Artifacts do not name inspiration products (t157u). Status stays Ready. No product code.

- CARD-120 walked rename-only (`.github/cards/` - CARD-120):
  - Walked lock recorded, not built. Rename-only after CARD-117 and CARD-121. Python `*Skill` modules (WikiSkill, GitSkill, CardSkill, etc. under `src/application/skills/`) are tool groups, not runbooks. After rename, skill in code means `SKILL.md`. No new features, no behavior change. `wiki_read` vs `wiki_write` split belongs to CARD-121, not extra scope here. Status stays Ready. No product code.

- CARD-117 walked change list 2026-08-30 (`.github/cards/` - CARD-117):
  - Walked lock recorded, not built. Skill = one SKILL.md runbook (stop saying skill pack for that file). Agent profile skill checklist next to Forge (`allowed_skill` ids; today `AgentProfile` only has `allowed_tool_names` in `src/domain/kernel/models.py`). Pack-owned skills ON with that agent; platform skills All Off except Assistant and AutoReiv. Untick omits name+blurb and refuses `skill_view` for that id. Prompt injects ticked names+blurbs; keep `skill_view` for body; drop must-call-list-first. `user_catalog.py` already lists name+description; only Assistant/AutoReiv/Agent Builder have those tools (`profiles.py`). Okta Admin = agent, user-provisioning = skill; no live Okta. CARD-118 studio freeze; CARD-120 Python `*Skill` rename. Status stays Ready. No product code.

- CARD-117/121 controls: platform All Off except Assistant/AutoReiv; pack-owned on; untick omits context (`.github/cards/` - CARD-117):
  - t154u lock recorded, not built. Ditch RBAC as the name. Two Agent Studio checkbox groups per agent: pack-owned come ON at create/import; platform/shared (`wiki_read`, `wiki_write` separate, etc.) default All Off except builtin Assistant and AutoReiv (those keep useful platform ticks we choose). Untick MUST omit tool schema / skill name+blurb from model context. Agent directory is name + one-line purpose only. No in-flight dynamic mapper. No pixel spec. CARD-119 roster epic not duplicated. CARD-121 one-line pointer. Status stays Ready. No product code.

- CARD-119 intent: core ship Assistant+AutoReiv; specialists as packs later (`.github/cards/` - CARD-119):
  - Later-discuss only. When Agent Packs are eventually implemented, shipped core roster is two agents: Assistant and AutoReiv. Specialists (Coding, Conductor, Review, Agent Builder, Okta Admin, EUC, etc.) arrive as Agent Packs (agent + skills + tools), not more builtins. Do not rip existing builtins on this card. Foundations first (CARD-117, 121, 120, workflow later). Memory CARD-116 last. CARD-122 unrelated low-priority. Controls notes (not this card to build): two Agent Studio checkbox groups (pack-owned vs small platform group); untick omits schema; no RBAC engine; no in-flight dynamic mapper; handoff is name+blurb directory. Status stays Ready. No product code.

- Opened low-priority CARD-122 three-beats skill idea (`.github/cards/` - CARD-122):
  - Later SKILL.md runbook for an autonomous coder working with a visionary (Jacob). Documents the 2026-08-30 three-beats working agreement. Ultra low priority. Do not pick up until CARD-117/121/120 (and workflow later) are in motion or done. Not a reason to build Skills Studio features. No product code.

- CARD-116 explore Mem0 then native; pickup after refactors (`docs/specs/per-agent-memory/` - CARD-116):
  - Research still Ready. Explore both Mem0 and a native/better-fit alternative (grow CARD-042 per-agent SQLite+Ollama, or whatever research shows is better). Do not lock Mem0. When later executed: start with Mem0 deep research, then compare. Pickup blocked until after the other pile (orchestration / Goal / loops / graphs) and foundation refactor cards (CARD-117, CARD-121, CARD-120, CARD-118; CARD-119 later-discuss). Memory is a bolt-on after those are ironed out. Three-shelf architecture kept. Wiki / Letta product / Zep product stay out. No product code.

- CARD-116 research leaning (`docs/specs/per-agent-memory/` - CARD-116):
  - Research leaning recorded (not a locked vendor purchase). Wiki / Letta product / Zep product: no. Mem0 to evaluate for archive (shelf 3). Three-shelf per-agent brain. No product code.

- Opened backlog CARD-121 tools ground-up (`.github/cards/` - CARD-121):
  - Alignment only. Tool = one atomic callable (name + description + parameters to the model every turn if allowlisted). Not a worker, not a runbook, not a skill pack. Ground-up: current Forge pack grouping, `manifest.py` skill-pack clustering, and Python `*_skill.py` tool modules are likely off/mixed. Working agreement recorded (walk with CARD-117/120; no silent-big-bang). No product code.

- CARD-117 points at the shared working agreement and CARD-121 (`.github/cards/` - CARD-117):
  - Short "When we pick this up" pointer. CARD-121 is the sibling tools pass, not a second definition of skill. No product code.

- Expanded CARD-117 skills primitive intent (`.github/cards/` - CARD-117):
  - Ground-up revisit recorded, not implemented. Intent expanded for controls, load path, levers, and built-in vs user-added. Current Skills Studio, `$DATA_DIR/skills` packs, `list_user_skill_packs` + `skill_view`, Python `*Skill` classes, and leftover orchestration `skills: List[str]` are likely off. Two explicit per-agent lists (tools already in Agent Studio; skills list missing). Load path: inject name+blurb every turn; body on open; extra list call is off vs progressive disclosure (name+blurb then body). Skill on/off levers next to the agent, not Skills Studio. CARD-118/119/120 cross-linked. No product code.

- Opened backlog CARD-117 skills primitive = one SKILL.md runbook (`.github/cards/` - CARD-117):
  - Alignment only. Skill = one runbook (order, pitfalls, done-when), not a skill pack, not a worker. Progressive disclosure name+description first; skill index is name+blurb only. Tools on the agent allowlist still go to the model every turn. Stop using Skill Pack for the primitive. Points at CARD-114 findings and prior art studied outside this repo. No product code.

- Opened backlog CARD-118 rethink or replace Skills Studio (`.github/cards/` - CARD-118):
  - Freeze only. Jacob's original studio organized before definitions were solid. Current studio edits `$DATA_DIR/skills` SKILL.md packs. Likely drop/replace later. No big studio features until CARD-117. No product code.

- Opened backlog CARD-119 Agent Packs later discussion (`.github/cards/` - CARD-119):
  - Conceptual packaging: ship an agent with its skills and tools (e.g. Okta Admin bundle). Not a fourth primitive. Not build-now. Discuss after agent/skill/tool foundations. No product code.

- Opened backlog CARD-120 rename Python *Skill modules (`.github/cards/` - CARD-120):
  - Refactor-and-alignment later. WikiSkill, GitSkill, CardSkill, etc. are tool groups, not runbooks. Skill in code should mean a SKILL.md runbook. Foundations first. No new features. No product code.

- Opened backlog CARD-116 per-agent memory research (`docs/specs/per-agent-memory/` - CARD-116):
  - Research only. Independent first-class brain per agent (not one markdown for all, not only Chat session history). Agent Studio fact-lifetime and other levers with hard min/max. Prior art studied outside this repo. No vendor pick. No product code.

- Remove Forge 12-tool allowlist warning (`AutoReiv.Web` - CARD-115):
  - Agent Studio no longer shows the CARD-078 amber banner when 12+ tools are checked. `FORGE_ALLOWLIST_WARN_AT` and `#forgeAllowlistWarning` are removed. Save and tool mounting are unchanged. No hard cap.

- Opened CARD-114 user intent review and product alignment (`docs/specs/user-intent-review/` - CARD-114):
  - Review artifact only. Findings SSOT at `docs/specs/user-intent-review/findings.md` (35 findings, verified on `qa`). No product code.

- Skills Studio archive and confirm-delete for user packs (`AutoReiv.Skills`, `AutoReiv.Web` - CARD-113):
  - Studio lists `$DATA_DIR/skills` user packs only. Python builtins (WikiSkill, execute_code, handoff) stay out (`[REQ-DATA-015]`).
  - Archive / Unarchive reuse CARD-112 `POST /api/skills/user-packs/{id}/archive`, unarchive, and `GET /api/skills/archived-packs`. Live list hides archived packs; Unarchive restores (`[REQ-DATA-015]` `[REQ-DATA-016]`).
  - `DELETE /api/skills/user-packs/{id}` requires `confirm=true` (400 without). Removes the jailed live dir and `_archive/<id>/` if present. Path traversal (`../`) is rejected (`[REQ-DATA-017]`).
  - Bundled seed `okta-admin` DELETE is 409 unless `confirm_seed=true`. Repo `src/infrastructure/skills/seeds/` is never deleted. UI uses `window.confirm` plus a second confirm for okta-admin (`[REQ-DATA-018]`).

- Skill curator stale/archive (`AutoReiv.Skills`, `AutoReiv.Routines` - CARD-112):
  - Unused user packs go active -> stale (30d) -> archive (90d). Archive is a directory move to `$DATA_DIR/skills/_archive/<id>/`. Live `SKILL.md` is never deleted (`[REQ-IMPROVE-013]`).
  - `okta-admin` / `BUNDLED_PACK_IDS` are never auto-archived or deleted. Repo `src/infrastructure/skills/seeds/` is untouched. Explicit confirm is required to archive a bundled pack (`[REQ-IMPROVE-014]`).
  - Unarchive is the reverse move. Dest-exists fails closed. Pack reappears in `GET /api/skills/user-packs` / Skills Studio. No `propose_skill` (`[REQ-IMPROVE-015]`).
  - Curator function + paused sibling routine `skill-curator` (`enabled=false`). CARD-111 harvest hook is off (`metadata.auto_archive=false`). Unknown last-used fails closed. Does not rewrite packs mid-chat-turn (`[REQ-IMPROVE-016]`).

- Nightly skill eval routine (`AutoReiv.Routines`, `AutoReiv.Skills` - CARD-111):
  - Seed `skill-eval-sleep` into existing `routines` / `BUILTIN_ROUTINES` targeting `agent-builder`. Same `RoutineExecutor` + `routine_runs`. No second scheduler. No `skillopt` pip (`[REQ-IMPROVE-007]` `[REQ-IMPROVE-012]`).
  - Default **paused** (`enabled=false`). When enabled, `next_run_at` is weekday 21:00 `America/New_York` (timezone-aware UTC instant). Not 02:00 local (surprise GPU load) and not 21:00 UTC (`[REQ-IMPROVE-008]`).
  - In-process job harvests failed `telemetry_spans` turns and FAILED jobs/phases from the live `$DATA_DIR` db (lookback 72h, capped). Refuses checkout `./data` when LocalAppData is live. Empty harvest is a success no-op (`[REQ-IMPROVE-009]`).
  - Replay optional and default off; honors generation slot default 1. Checker must pass to stage; missing named checker is honest skip. Stage is CARD-106 `propose_skill` draft only (`auto_commit` false). No `SKILL.md` write, no `commit_skill_pack`, no `stream_turn` child phase (`[REQ-IMPROVE-010]` `[REQ-IMPROVE-011]` `[REQ-IMPROVE-016]`).

- ACE-style online playbook notes + snapshot/rollback (`AutoReiv.Skills`, `AutoReiv.Kernel`, `AutoReiv.Orchestration` - CARD-110):
  - Failed turn / checker miss produces at most one tiny ACE delta. Generator is existing `AgentKernel`. In-process Reflector + Curator. No second kernel, LangGraph, or ACE vendor (`[REQ-IMPROVE-001]` `[REQ-IMPROVE-002]`).
  - Online path parks a CARD-106 `propose_skill` draft (`ace_delta`, snapshot id). Live `SKILL.md` is not rewritten in the turn. Python-shaped deltas stay `propose_tool` drafts with `requires human/code card`. No `src/` writes (`[REQ-IMPROVE-003]` `[REQ-IMPROVE-005]`).
  - `UserSkillCatalog` snapshots `SKILL.md` + sidecar notes under `$DATA_DIR/skills/<id>/snapshots/<utc-iso>/` before apply. Rollback restores bytes. Snapshot I/O failure skips apply (`[REQ-IMPROVE-004]`).
  - Optional append-only `PLAYBOOK_NOTES.md` / `notes.jsonl` sidecar does not modify `SKILL.md`. Promotion into the playbook is still `propose_skill`. Online path does not enqueue nightly eval (`[REQ-IMPROVE-006]` `[REQ-IMPROVE-016]`).

- Skill self-improve (`docs/specs/skill-self-improve/` - CARD-110-112): spec and Slice D cards opened. ACE-style online playbook deltas with snapshot/rollback (HITL `propose_skill` if writing SKILL.md), nightly SkillOpt-Sleep-shaped eval routine on the existing routines table (21:00 America/New_York weekdays, default paused, validation gate), skill curator stale user-pack archive (never delete bundled/okta-admin). No feature code. No push. No DB wipe.


- Windows launcher uses data dir (`AutoReiv.Deploy` - CARD-109):
  - `deploy/windows/run_autoreiv.ps1` no longer defaults `--db-path` / `--wiki-path` (or `AUTOREIV_DB_PATH` / `AUTOREIV_WIKI_PATH`) to checkout `./data`. Default Windows boot (including `-Reload`) lets `DataDirResolver` open `%LOCALAPPDATA%\AutoReiv` for db, wiki, and skills (`[REQ-DATA-001]`, `[REQ-DATA-003]`).
  - Explicit `AUTOREIV_DB_PATH` / `-DbPath` / `--db-path` still win when they are not the checkout legacy path. Leftover checkout env from an old launcher session is stripped.

- Okta admin skill pack scaffold (`AutoReiv.Skills` - CARD-108):
  - Bundled agentskills.io pack `okta-admin` at `src/infrastructure/skills/seeds/okta-admin/SKILL.md` is copy-if-missing seeded into `$DATA_DIR/skills/okta-admin/SKILL.md` on data-dir bootstrap. Existing dest is left alone so user edits survive a second boot (`[REQ-BUILD-015]`).
  - Playbook SOP (list users, groups, conceptual MFA reset/unlock, assign app) plus JSON tool stubs. No live Okta API, no credentials, no Okta env keys, no Python Okta SDK in `src/` (`[REQ-BUILD-016]`).

- Agent Builder specialist writes approved skill packs (`AutoReiv.Agents`, `AutoReiv.Skills`, `AutoReiv.Orchestration` - CARD-107):
  - Builtin `agent-builder` Chat specialist (not Conductor). Allowlist stays under 12: lookup, propose_*, list packs, skill_view, commit_skill_pack, agent-spec tools, handoff. No execute_code, git, or card writes (`[REQ-BUILD-009]`).
  - New tools stay on existing `AgentBuilderSkill`. `commit_skill_pack` writes approved skill/tool/workflow proposals through `UserSkillCatalog.save_pack` into `$DATA_DIR/skills` (same files Skills Studio edits). Draft/rejected fail closed. Python stubs never write `src/` (`[REQ-BUILD-010]` `[REQ-BUILD-012]` `[REQ-BUILD-014]`).
  - Default Chat is one Job + one Phase + `stream_turn`. Goal mode uses the CARD-099 no-tool planner with linear research phases (survey, draft playbook, declare tools, HITL propose). Research does not write `SKILL.md` (`[REQ-BUILD-011]`).
  - Soft CARD-078 sprawl / extend-specialist warning is visible before commit and on `save_agent_specification`. Not a hard gate (`[REQ-BUILD-013]`). Approve still does not write disk; commit is the write.

- propose_skill / propose_tool / propose_workflow HITL drafts (`AutoReiv.Skills`, `AutoReiv.Orchestration` - CARD-106):
  - Tools on existing `AgentBuilderSkill` write a `proposals` row (`kind` skill|tool|workflow, `status` draft) plus a Chat HITL `pending_approvals` park (`[REQ-BUILD-001]` `[REQ-BUILD-002]` `[REQ-BUILD-003]` `[REQ-BUILD-007]`).
  - Payload is what / why / how / where, jailed under `$DATA_DIR/skills`. Missing field fails closed. No `SKILL.md` write. No Python under `src/`. Workflow is playbook SOP, not job-template YAML (`[REQ-BUILD-004]` `[REQ-BUILD-005]`).
  - Approve marks `approved` and does **not** write disk. Reject marks `rejected`. Pack commit is CARD-107. Tool drafts that look like Python builtins stay draft-only with note `requires human/code card` (`[REQ-BUILD-008]`).
  - Soft CARD-078 sprawl warning when the target allowlist would be >= 12 or a new agent is preferred over extending a specialist. Does not block the draft (`[REQ-BUILD-006]`).
  - Allowlisted on Assistant and AutoReiv (discovery). Not Coding, Review, or Conductor. `save_agent_specification` unchanged (immediate, no HITL).


- Agent Builder HITL (`docs/specs/agent-builder-hitl/` - CARD-106-108): spec and Slice C cards opened. `propose_skill` / `propose_tool` / `propose_workflow` HITL drafts on existing AgentBuilderSkill, Agent Builder specialist wired to Job/Phase + data_dir skills, Okta admin pack scaffold. No feature code. No push.

- Skills Studio UI (`AutoReiv.Web`, `AutoReiv.Skills` - CARD-105):
  - Sibling tab of Agent Studio lists user packs from `$DATA_DIR/skills` (name + description) and reads/edits `SKILL.md` on disk. Disk is the source of truth (`[REQ-DATA-012]`).
  - Opening a pack lists JSON tools parsed from that `SKILL.md`. No tool blocks yields an empty list (playbook-only packs are valid) (`[REQ-DATA-013]`).
  - Job templates are a later placeholder only. Playbook SOP is the SKILL.md body; `jobs.template_id` stays nullable (`[REQ-DATA-014]`).
  - `GET/POST /api/skills/user-packs` and `GET/PUT /api/skills/user-packs/{id}` are jailed to the skills tree. Saves match Forge (direct write, no HITL). Writes do not land in repo `.agents/skills`.

- User agentskills.io packs (`AutoReiv.Skills` - CARD-104):
  - Bootstrap scans `$DATA_DIR/skills/**/SKILL.md` via `DynamicSkillLoader.list_skill_manifests` (frontmatter name + description + path only). Python builtins still register when `skills/` is missing (`[REQ-DATA-009]`, `[REQ-DATA-010]`).
  - `skill_view` loads the SKILL.md body and JSON tool blocks on demand. Colliding user tool names are skipped; builtin Python tools win (`[REQ-DATA-011]`). Pack JSON is not executed as Python.
  - User-pack tools still go through each agent's Forge `allowed_tool_names`. `list_user_skill_packs` and `skill_view` are allowlisted on Assistant and AutoReiv only. Repo `.agents/skills` packs are not auto-mounted.

- Backup and restore of the data dir (`AutoReiv.Data` - CARD-103):
  - `DataDirBackupService` zips the resolved data dir (`autoreiv.db`, wiki, skills, and other tree files) to a timestamped archive under `$DATA_DIR/backups/` (or a user-chosen path). SQLite is snapshotted via the backup API. Checkout source, venv, and `backups/` itself are not included (`[REQ-DATA-007]`).
  - Confirmed restore (`autoreiv restore <src.zip> --yes` / Settings Restore) replaces the tree after extracting to a staging area. Cancel and missing `autoreiv.db` leave the live tree unchanged. A pre-restore zip is kept under `backups/` (`[REQ-DATA-008]`).
  - `POST /api/data-dir/backup` (zip download) and `POST /api/data-dir/restore` (multipart zip, `confirm=true`). Settings Studio Backup / Restore next to the CARD-102 data-dir panel.

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
  - Harmonized Purpose-Based Model Routing with auto-populated dropdowns bound directly to discovered models.
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
- Purpose-Based Model Routing (`ModelPurposeMatrix`) for `GENERAL`, `REASONING`, `TASK_EXECUTION`, `VISION`, `AUXILIARY`, and `FAST` operational roles.
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



