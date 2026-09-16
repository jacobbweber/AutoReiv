# Architecture Design: Unified Platform Agent & Dynamic Tool Scoping

> **Status**: Draft / Proposed  
> **Card Reference**: [CARD-339](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-339-skill-and-tool-architecture-and-scoping-strategy.md)  
> **ADR Reference**: ADR-0052 (Pending)  
> **Author**: Jacob Weber & Antigravity  
> **Date**: 2026-09-16  

---

## 1. Executive Summary & Problem Statement

AutoReiv's telemetry audit in Observe Studio revealed an unsustainable "harness tax": chatting with the built-in `autoreiv` agent currently serializes **40 full JSON function schemas**, consuming **16,164 tokens (52.3% of the prompt)** on every single conversational turn.

Simultaneously, the platform suffers from **Platform Agent Sprawl**:
- The platform previously separated core operating system functionality across multiple built-in agents (`assistant`, `autoreiv`, `wiki`, `developer`).
- This artificial separation introduced heavy cognitive load for the operator ("which agent do I talk to?"), unnecessary `handoff_to_agent` handshakes, permission deadlocks (Assistant cannot write to the Wiki), and orchestration failures in multi-step jobs (CARD-336).

This document establishes the architecture to:
1. **Consolidate Built-in Agents** into a **Single Unified Platform Agent (`AutoReiv`)** equipped with modular platform skills.
2. Preserve **Custom Agent Packs** for genuine, portable user-created domain specialists (e.g. Tutor, Homelab Architect).
3. Implement a **Hybrid Dynamic Tool Scoping Engine** (Fast-Path Intent Detection + Autonomous Progressive Disclosure via `activate_skill`) to shrink prompt tool overhead from 16,164 tokens down to ~1,200 tokens (<10%).

---

## 2. The Core Primitives: Clarifying Definitions

| Primitive | What It Represents | Architectural Contract | Implementation |
| :--- | :--- | :--- | :--- |
| **Tool** | **The Hands and Feet** | An atomic, executable Python function that performs an action, I/O, or data retrieval. Sandboxed, typed, and stateless. | A Python callable registered in `ScopedToolRegistry` with a JSON schema. |
| **Skill** | **The Brain / SOP** | A procedural runbook instructing the agent *when*, *why*, and in what *sequence* to use specific tools to accomplish a high-level goal. | A modular Markdown document (`SKILL.md`) with YAML frontmatter. |
| **Platform Agent** | **The Operating System** | The single built-in companion (`AutoReiv`) that possesses core platform capabilities. | Built-in persona with access to core platform skills. |
| **Custom Agent Pack** | **The Domain Specialist** | A portable, exportable package defining an external specialist with a custom prompt, private memory DB, and domain tools. | A folder under `packs/<id>/` containing `pack.json`, skills, and memory. |

---

## 3. Platform Agent Consolidation

### 3.1 The "Single Built-in Agent" Architecture
Rather than forcing the operator to choose between `assistant`, `wiki`, and `autoreiv`, AutoReiv provides:
- **`direct`**: The zero-tool, zero-skill raw model benchmark agent.
- **`autoreiv`**: The single, hyper-capable built-in platform agent.

Capabilities previously fractured across separate built-in agents are reorganized into **Modular Platform Skills**:
1. **`skills/wiki/` (Knowledge & Notes)**:
   - Tools: `wiki_note_read`, `wiki_note_search`, `wiki_note_create`, `wiki_note_update`, `list_wiki_templates`.
   - Runbook: Enforces structured note creation, canonical vault grounding, and inbox staging (`00_Inbox/`).
2. **`skills/diagnostics/` (Platform Health & SRE)**:
   - Tools: `inspect_system_health`, `get_system_logs`, `get_recent_errors`, `get_tool_health_matrix`, `cli_exec`.
   - Runbook: Host telemetry inspection, safe diagnostic execution, and error triage.
3. **`skills/tasks/` (Daily Organization & Workflows)**:
   - Tools: `get_or_create_weekly_note`, `log_daily_work_item`, `complete_weekly_task`, `rollover_weekly_tasks`.
   - Runbook: Workflow coordination, weekly reviews, and task scheduling.
4. **`skills/coding/` (Repository Code & Sandbox)**:
   - Tools: `repo_file_read`, `repo_file_list`, `repo_file_write`, `repo_file_patch`, `execute_code`.
   - Runbook: Guarded repo inspection and HITL-confirmed modifications.

### 3.2 Preserving Custom Agent Packs
Custom Agent Packs remain untouched and serve their true architectural purpose:
- **Domain Specialization**: E.g., `tutor` (education mastery ladders), `homelab-architect` (infrastructure & VLANs).
- **Portability**: Packs can be created in Agent Studio, exported as ZIP/JSON, shared, or imported.
- **Group Collaboration**: In Group Chat (CARD-340), the operator can bring `autoreiv` and multiple custom agent packs into the same room.

---

## 4. The Dynamic Tool Scoping Engine

To prevent the consolidated `autoreiv` agent from loading all 40+ tool schemas simultaneously, the kernel uses a **Two-Layer Hybrid Engine**:

```
                              [ Incoming User Message ]
                                          │
                                          ▼
                       ┌─────────────────────────────────────┐
                       │ Layer 1: Fast-Path Intent Matcher   │
                       │ (Deterministic, 0ms, Zero LLM cost) │
                       └──────────────────┬──────────────────┘
                                          │
                    Matches obvious       │     Subtle / Ambiguous
                    intent keywords       │     or multi-phase
                                          │
                         ▼                │                 ▼
       ┌───────────────────────────┐      │      ┌───────────────────────────┐
       │ Mount Lean Base           │      │      │ Mount Lean Base ONLY:     │
       │ + Matched Skill Tools     │      │      │ • activate_skill          │
       │ (e.g. diagnostics tools)  │      │      │ • ask_clarification       │
       │ Schema: ~2,000 tokens     │      │      │ • handoff_to_agent        │
       └─────────────┬─────────────┘      │      │ Schema: ~800 tokens       │
                     │                    │      └─────────────┬─────────────┘
                     │                    │                    │
                     ▼                    │                    ▼
       ┌───────────────────────────┐      │      ┌───────────────────────────┐
       │ Layer 2: Model Execution  │◄─────┘      │ Model calls:              │
       │ Answers / acts in 1 turn  │             │ activate_skill("wiki")    │
       └───────────────────────────┘             └─────────────┬─────────────┘
                                                               │
                                                               ▼
                                                 ┌───────────────────────────┐
                                                 │ Kernel mounts wiki tools  │
                                                 │ for Step 2 of the turn    │
                                                 └───────────────────────────┘
```

### 4.1 The Lean Base Tools (~800 tokens)
Every conversational turn begins with only the core primitives:
1. `activate_skill(skills: list[str])`: Dynamically unlocks additional skill tool sets mid-turn.
2. `ask_clarification(question: str)`: Asks the human operator for missing details.
3. `handoff_to_agent(target_agent: str, task: str)`: Hands off to custom specialist agent packs.

### 4.2 Layer 1: Fast-Path Intent Detection (90% of Turns)
- When the user's prompt contains clear intent triggers (e.g. `"health"`, `"logs"`, `"note"`, `"weekly task"`), the kernel automatically pre-mounts that skill's tools *before Step 1 begins*.
- **Latency**: 0ms (regex/keyword matcher).
- **Token overhead**: Adds only ~3–4 tools (~1,200 tokens).
- **Outcome**: The model responds or executes immediately in a single turn without needing an extra tool call.

### 4.3 Layer 2: Autonomous Progressive Disclosure (`activate_skill`) (10% Fallback)
- If the prompt is phrased subtly or requires multiple disciplines, the model inspects its available skills catalogue and calls:
  `activate_skill(skills=["wiki", "diagnostics"])`
- The kernel intercepts this call locally, loads the requested skill runbooks and tool schemas, and resumes the turn.
- **Context Isolation**: The tool schemas are injected *ephemerally into that execution loop only*. They do not permanently pollute the SQLite `chat_messages` table.

---

## 5. Elimination of Job Delegation Deadlocks (CARD-336)

By consolidating platform skills into `autoreiv`:
1. When a multi-step job requires platform capabilities (e.g., inspecting logs and creating a wiki note), `autoreiv` can formulate AND execute both phases without fail-closed permission blocks.
2. When a multi-step job requires a **custom domain specialist** (e.g. `tutor` or `homelab`):
   - `create_job_from_catalog_resolve()` resolves the specialist's pack.
   - The orchestrator stamps `assigned_agent_id = "<specialist_id>"` for the execution phase.
   - The formulated parameters are passed cleanly across phase boundaries.

---

## 6. Verification & Telemetry Targets

| Metric | Current State (CARD-337 Baseline) | Target State (Post CARD-339) |
| :--- | :--- | :--- |
| **Tool Count in Prompt** | 40 tools | 3 to 6 tools |
| **Tool Schema Tokens** | 16,164 tokens (52.3%) | 1,200 to 2,500 tokens (<15%) |
| **Observe Studio Bloat Alert** | Triggered (>50%) | Cleared (<15%) |
| **Time to First Token (TTFT)** | Inflated by 16k schema processing | Instantaneous |
| **Platform Agent Selection** | 4 confusing platform agents | 1 primary AutoReiv agent + custom packs |
| **Cross-Domain Job Success** | Fails closed on wiki writes | Executes seamlessly |
