# [ADR-0052] Skill and Tool Dynamic Scoping, Platform Consolidation & Specialist Dispatch

> **Status**: Accepted  
> **Date**: 2026-09-16  
> **Deciders**: Jacob (Visionary & Product Owner), Antigravity (Principal Software Engineer)  
> **Card Reference**: [CARD-339](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-339-skill-and-tool-architecture-and-scoping-strategy.md)  
> **Spec Reference**: `docs/specs/skill-and-tool-architecture-and-scoping-strategy/design.md`  

---

## Context

AutoReiv telemetry audits revealed an unsustainable 16k "Harness Tax": conversational turns with the built-in companion loaded 40 full JSON function schemas, consuming 16,164 tokens (52.3% of the context window) on every turn before user input was processed.

Simultaneously, AutoReiv suffered from architectural fragmentation:
1. **Platform Agent Sprawl**: Core system capabilities were fractured across competing built-ins (`assistant`, `wiki`, `autoreiv`, `developer`), creating operator confusion and unnecessary handoffs.
2. **Specialist Dispatch Deadlock (CARD-336)**: Job orchestrators locked multi-phase execution to front-of-house intake agents, failing closed when specialist tools (`wiki_note_*`) were needed during execution phases.
3. **Primitive Ambiguity**: The boundaries between executable Python tools ("Hands") and procedural Markdown SOP runbooks ("Brain") were blurred, leading to bloated static tool manifests.

## Decision

We establish four architectural pillars:

### 1. Strict Primitive Definitions
- **Tool ("Hands")**: An atomic, typed, executable Python callable registered in `ScopedToolRegistry`. Stateless, sandboxed, and invoked via JSON schemas.
- **Skill ("Brain")**: A modular procedural Markdown SOP runbook (`SKILL.md`) with YAML frontmatter instructing an agent when, why, and in what sequence to invoke tools to achieve an operational outcome.
- **Platform Agent**: The single unified built-in companion (`autoreiv`) equipped with modular platform skills, alongside the zero-tool raw benchmark agent (`direct`).
- **Custom Agent Pack**: A portable domain specialist stored in user data (`packs/<id>/`) defining custom system prompts, private memory databases, and specialized tools.

### 2. Built-in Platform Consolidation
- Consolidate built-ins into `autoreiv` (primary companion) and `direct` (raw baseline).
- Deprecate `assistant`, `wiki`, and `developer` as separate built-ins. Ensure backward compatibility via `canonical_agent_id` alias resolution so existing session histories and API calls resolve `autoreiv` seamlessly without 404 errors.
- Package platform capabilities into modular platform skills:
  - `skills/wiki/`: `wiki_note_read`, `wiki_note_search`, `wiki_note_create`, `wiki_note_update`, `list_wiki_templates`.
  - `skills/diagnostics/`: `inspect_system_health`, `get_system_logs`, `get_recent_errors`, `get_tool_health_matrix`, `cli_exec`.
  - `skills/tasks/`: `get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`.
  - `skills/coding/`: `repo_file_read`, `repo_file_list`, `repo_file_write`, `repo_file_patch`, `execute_code`.

### 3. Lean Platform Baseline & Two-Layer Dynamic Tool Scoping
- Shrink `REQUIRED_PLATFORM_TOOLS` down to 5 Lean Platform Primitives:
  1. `activate_skill(skills: list[str])`: Dynamically unlock domain skill tools during execution.
  2. `ask_clarification(question: str)`: Request operator clarification.
  3. `handoff_to_agent(target_agent: str, task: str)`: Delegate to specialist packs.
  4. `lookup_agents()`: Discover available agents.
  5. `get_session_info()`: Retrieve active session metadata.
- **Layer 1 (Fast-Path Intent Matcher)**: Deterministic 0ms keyword/regex matcher before turn Step 1 pre-mounts domain skill tools when obvious intent keywords are detected.
- **Layer 2 (Autonomous Progressive Disclosure)**: For ambiguous queries, the model calls `activate_skill` to unlock domain tools on demand.
- **Ephemeral Context Isolation**: Dynamically mounted tool schemas exist strictly within the turn execution loop without permanently mutating agent profiles or polluting SQLite storage tables.

### 4. Specialist Intake Dispatch (CARD-336 Resolution)
- In `create_job_from_catalog_resolve()`: when multi-step tasks require specialist capabilities (e.g. Wiki document reorganization or domain fleet actions), assign the execution phase to that specialist agent (`assigned_agent_id`) or mount the required skill, passing formulated parameters across phase boundaries without fail-closed stalls.

## Consequences

- **Positive**:
  - Prompt tool schema overhead slashed from 16,164 tokens (>50%) to <1,500 tokens (<10%), cutting token costs and drastically reducing Time to First Token (TTFT).
  - Clear mental model for operators: talk to `autoreiv` for all platform jobs, or talk to specialized custom packs.
  - Multi-step job execution completes successfully without permission deadlocks.
- **Negative / Trade-offs**:
  - Ambiguous queries that require Layer 2 progressive disclosure consume an extra model step to call `activate_skill`.
  - Legacy test suites and pack manifests expecting static 40-tool lists must be updated to align with dynamic scoping.

## Compliance & Verification

- Validated via `pytest tests/unit/agent_packs/`, `pytest tests/unit/kernel/`, and `pytest tests/unit/orchestration/`.
- Verified live on Jarvis (`http://192.168.1.99:8000`) with empirical token counts in Observe Studio.
