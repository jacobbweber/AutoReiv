---
id: CARD-407
title: "Fix Capability Catalog Seeding, Tool Policy Gate Empty Fallback, and AutoReiv Pack Health Tools"
status: Done
created: 2026-09-21
adr: none
labels:
  - type:bug
  - area:orchestration
  - area:safety
  - area:agents
  - area:wiki
---

# [CARD-407] Fix Capability Catalog Seeding, Tool Policy Gate Empty Fallback, and AutoReiv Pack Health Tools

> **Status**: Done  
> **Created**: 2026-09-21  
> **ADR Reference**: none  
> **Labels**: `type:bug`, `area:orchestration`, `area:safety`, `area:agents`, `area:wiki`  

---

## 1. Why / Intent (Beat 1: What Jacob Means)

1. **AutoReiv Platform Health vs. Raw Shell Diagnostics**:
   AutoReiv is the platform SRE, companion, and wiki vault curator. When tasked with a "system health check", AutoReiv must evaluate the health of the AutoReiv platform itself using its built-in telemetry tools (`inspect_system_health`, `get_tool_health_matrix`, `get_recent_errors`, `get_system_logs`, `system_info`), rather than attempting to execute raw host bash/shell commands like `uname` or `uptime`.
2. **Strict Agent Role Boundaries (AutoReiv vs. Developer)**:
   Arbitrary terminal/shell command execution belongs strictly to the `developer` agent. If a task requires host CLI debugging, AutoReiv should hand off to `developer` via `handoff_to_agent("developer", ...)`. AutoReiv's `platform-health` skill must not bundle `cli_exec`.
3. **Wiki Note Intake (One-Door Policy)**:
   When an agent creates a note in the wiki, it must search/read templates from `02_Resources/_Templates/` and land the new note strictly in `00_Inbox/` (`category="inbox"`). Downstream processes (such as the `wiki-curation` routine or operator review) groom, clean up frontmatter, and migrate notes to `01_Notes/`. The single turn or job must not attempt to bypass the Inbox or force warehouse migration.
4. **Startup Capability Catalog Indexing**:
   The capability catalog (`capability_index` in SQLite) must be seeded at startup with trusted built-in tools, agents, and pack skills so that `CapabilityCatalogResolver` can match capabilities for multi-step goals instead of returning empty results.
5. **Tool Policy Gate Empty Fallback**:
   When a multi-step job has no matched capability subset (`matched_capability_ids` is empty or resolves to no tools), the safety policy gate (`ToolPolicyGate`) must fall back to evaluating the agent's own assigned allowlist and dangerous command filters rather than treating an empty subset as `set()` and hard-blocking 100% of all tool calls.

---

## 2. What AutoReiv Does Now (Beat 2)

1. **Cold-Start Capability Index Vacuity**:
   `capability_index` in `autoreiv.db` contains 0 rows on boot because no startup routine seeds built-in tools or agents into `CapabilityCatalogRepository`.
2. **Lockout on Empty Capability Subset**:
   When a user submits an outcome-shaped prompt (*"do a system health check, and then save that note to the wiki; success is when..."*), `create_job_from_catalog_resolve` is invoked. Because `capability_index` is empty, `matched_ids` is `[]`.
   In `src/application/safety/tool_policy_gate.py`:
   `_capability_tool_names([])` returns an empty set `set()`. `ToolPolicyGate.evaluate()` checks `if subset is not None and not _name_in_matched_subset(name, subset)` and blocks EVERY tool with:
   `Tool '<name>' is out of matched capability subset ([]) - fail closed`.
   The agent is completely paralyzed, cannot run any tools (not even wiki reads or handoffs), loops 10 times, and fails the job.
3. **AutoReiv Pack Tooling Pollution**:
   In `platform-packs/autoreiv/pack.json`, `cli_exec` is included under the `platform-health` skill. When asked for a health check, the agent tries to run Linux shell commands (`uname -a && uptime && df -h / && free -m`) which fails on Windows and violates AutoReiv's SRE domain boundaries.

---

## 3. What Will Change (Beat 3)

1. **Safety Policy Gate Empty Fallback (`src/application/safety/tool_policy_gate.py`)**:
   - Update `_capability_tool_names(matched_capability_ids)`:
     If `matched_capability_ids` is empty or contains no tools and no tool capabilities, return `None`.
   - When `subset is None`, `ToolPolicyGate` falls back to the agent's allowlist, registry existence, and safety/HITL gates. This prevents the empty-set paralysis bug while preserving capability restriction when explicit tools are matched.
2. **Startup Capability Catalog Seeding (`src/web/app.py`, `src/application/capabilities/seeder.py`)**:
   - Implement `seed_builtin_capabilities(store, tool_registry, agent_registry, user_skill_catalog)` called on startup.
   - Index built-in tools (`kind=CapabilityKind.TOOL`, `trust_tier=TrustTier.TRUSTED`), built-in agents (`kind=CapabilityKind.AGENT`), and pack skills (`kind=CapabilityKind.SKILL`).
3. **AutoReiv Pack Definition & System Prompt Alignment (`platform-packs/autoreiv/pack.json`)**:
   - Remove `cli_exec` from `platform-health` in `platform-packs/autoreiv/pack.json`.
   - Update `autoreiv` system prompt to emphasize:
     - Use `inspect_system_health`, `get_tool_health_matrix`, `get_recent_errors`, `get_system_logs`, and `system_info` for AutoReiv platform health.
     - Shell commands belong to `developer`; use `handoff_to_agent("developer", ...)` if terminal execution is ever needed.
     - Follow the One-Door Policy: always create notes in `00_Inbox/` and do not attempt manual warehouse graduation.
   - Sync pack updates to user data (`packs/autoreiv/pack.json`).
4. **Max Turns Ceiling Expansion (1–1000) & Agent Studio Persistence**:
   - Raise `max_turns` upper bound from 50 to 1000 in `AgentProfile` and `AgentProfileGuardrail`.
   - Update Agent Studio UI (`index.html`) to allow `min="1" max="1000"` with explicit helper description.
   - Improve UI error toast formatting in `forge.js` to unpack FastAPI 422 validation detail arrays.
   - Sync `max_turns`, `tone`, and `history_retention_days` to `pack.json` during profile updates.
5. **Defensive Tag Coercion (`src/domain/wiki/frontmatter.py`)**:
   - Add pre-validators to `WikiInboxNoteMeta` and `WikiNoteMeta` to coerce stringified JSON lists (`'["tag"]'`) and comma-delimited strings into valid `list[str]`, preventing ReAct tool error loops.

---

## 4. What Dies Today (The Prune List - Beat 4)

- **PRUNE**: `cli_exec` from `platform-health` in `platform-packs/autoreiv/pack.json` and user data `packs/autoreiv/pack.json`.
- **PRUNE**: `sdlc-engineering` duplicate skill from `platform-packs/autoreiv/pack.json` and `platform-packs/autoreiv/skills/sdlc-engineering/` (software engineering belongs exclusively to `developer`).
- **PRUNE**: `read_project_file`, `write_project_file`, `list_project_dir`, `execute_code` from `autoreiv`'s `pack_tool_names`.
- **PRUNE**: Empty-set blocking in `_capability_tool_names()` in `src/application/safety/tool_policy_gate.py` that forced `subset = set()` when `matched_capability_ids == []`.
- **PRUNE**: Zero-seeding cold-start state of `capability_index` in `src/web/app.py`.
- **PRUNE**: Rigid `le=50` and `max_turns > 50` validation ceilings in `models.py`, `guardrails.py`, and `index.html`.
- **PRUNE**: Unhandled `[object Object]` toast formatting in `forge.js`.
- **PRUNE**: Unhandled raw string rejection on `tags` in `WikiInboxNoteMeta` / `WikiNoteMeta`.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-407-001] Capability Index Seeding**:
  - *Ubiquitous*: THE SYSTEM SHALL seed built-in tools, built-in agents, and platform skills into `capability_index` on server startup with `TrustTier.TRUSTED`.
- **[REQ-407-002] Capability Catalog Matching**:
  - *Event-Driven*: WHEN a user prompts for a multi-step task involving system health and wiki notes, THE SYSTEM SHALL match relevant indexed capabilities (`inspect_system_health`, `wiki_note_create`, etc.) instead of returning an empty subset.
- **[REQ-407-003] Tool Policy Gate Non-Blocking Fallback**:
  - *Event-Driven*: WHEN a multi-step job has an empty `matched_capability_ids` list (`[]`), `ToolPolicyGate` SHALL fall back to the agent's allowlist and NOT block tools with `"out of matched capability subset ([])"`.
- **[REQ-407-004] AutoReiv Pack Health Tool Scope**:
  - *Negative Assertion*: Automated tests SHALL assert that `cli_exec` is NOT present in `autoreiv`'s `platform-health` skill tools list in `platform-packs/autoreiv/pack.json`.
- **[REQ-407-005] AutoReiv Telemetry Diagnostic Verification**:
  - *Event-Driven*: WHEN AutoReiv executes a platform health check, THE SYSTEM SHALL invoke `inspect_system_health` or `get_tool_health_matrix` and create the resulting summary note in `00_Inbox/`.
- **[REQ-407-006] Max Turns Range Expansion (1–1000)**:
  - *Ubiquitous*: THE SYSTEM SHALL allow `max_turns` values between 1 and 1000 inclusive in `AgentProfile`, `AgentProfileGuardrail`, and Agent Studio UI inputs, persisting them to `autoreiv.db` and user-data `pack.json`.
- **[REQ-407-007] Defensive Wiki Tag Deserialization**:
  - *Event-Driven*: WHEN an LLM or caller passes `tags` as a stringified JSON array (e.g. `'["system-health"]'`) or comma-separated string to `wiki_note_create` or `WikiInboxNoteMeta`, THE SYSTEM SHALL automatically deserialize and clean it into a `list[str]` without raising a Pydantic validation error.
- **[REQ-407-008] Agent Studio Validation Toast Clarity**:
  - *Event-Driven*: WHEN saving an agent returns HTTP 422 with validation errors, Agent Studio SHALL display a formatted human-readable error message instead of `[object Object]`.

---

## 6. Constraints & Verification Plan

### Automated Tests
- `pytest tests/unit/safety/test_tool_policy_gate.py`: Verify empty `matched_capability_ids` does not block allowlisted tools.
- `pytest tests/unit/capabilities/test_capability_seeder.py`: Verify built-in tools and agents are seeded into `capability_index` with `TRUSTED` tier.
- `pytest tests/unit/agents/test_autoreiv_pack_alignment.py`: Verify `cli_exec` is absent from `autoreiv`'s `platform-health` skill.
- `pytest tests/unit/agents/test_agent_guardrails.py`: Verify `max_turns` up to 1000 is accepted and >1000 is rejected.
- `pytest tests/unit/wiki/test_wiki_frontmatter.py`: Verify stringified JSON and comma-delimited `tags` are parsed into `list[str]`.
- Full regression suite: `uv run pytest tests/unit/` + `npm run test:unit:frontend` + `npm run lint:frontend` + `uv run ruff check src/ tests/`.

### Manual Verification
- In Chat Studio with `autoreiv`, send: `"hi, can you do a system health check, and then save that note to the wiki; success is when the note lives in the wiki and a can read it"`.
- Verify the multi-step job successfully executes using `inspect_system_health` and `wiki_note_create` in `00_Inbox/`, claiming success without turn budget exhaustion or capability subset block errors.
- In Agent Studio, set Max Turns to 100 or 1000, save profile, refresh, and verify the value persists.
