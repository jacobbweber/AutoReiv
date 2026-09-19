# [ADR-0054] Autonomic Operating System, Demand-Paged Capabilities & Mechanical Governance

> **Status**: Accepted  
> **Date**: 2026-09-18  
> **Deciders**: Jacob (Visionary & Product Owner), Antigravity (Principal SDLC Engineer)  
> **Consulted**: AutoReiv Core Architecture  
> **Supersedes / Retires**: [CARD-340](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-340-multi-agent-group-chat-and-peer-to-peer-collaborative-conversation.md) (Multi-Agent Group Chat Roundtable Anti-Pattern)  
> **Related Cards**: [CARD-339](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-339-skill-and-tool-architecture-and-scoping-strategy.md), [CARD-361](file:///d:/Projects/Active/AutoReiv/docs/cards/CARD-361-dual-engine-front-door-autoreiv-core-and-direct-mode.md) through CARD-365  
> **Permanent Research Reference**: `D:\Projects\research\autoreiv-architecture-realignment-conways-law-and-autonomic-os.md`

---

## 1. Context & Problem Statement

AutoReiv's telemetry audit (CARD-339) revealed a critical bottleneck: conversational turns with the default companion loaded 40 function JSON schemas, consuming 16,164 tokens (52.3% of prompt context) on every turn before user input was processed. Furthermore, recent exploratory designs proposed a multi-agent "group chat" roundtable (CARD-340) where distinct personas (e.g., Assistant, Developer, Wiki, Tutor) would converse with each other in an open roundtable.

Rigorous architectural analysis of **Conway’s Law** and systems engineering (Casey Muratori's theorem on inter-worker communication latency) demonstrated that:
1. **Multi-Agent Conversational Sprawl is an Anti-Pattern**: When inter-agent communication is slower, lossier, and more rigid than internal model attention, splitting tasks across conversational agents creates token explosion, catastrophic latency, and the "telephone game" failure mode.
2. **Personas are Superficial Fluff**: LLM intelligence resides in foundation parametric weights. A "Homelab Agent" or "Developer Agent" prompt does not expand cognitive capacity; capabilities are governed entirely by **Tools (Syscalls)** and **Skills (Procedural Runbooks)**.
3. **The False Binary (Multi-Agent vs. God-Agent)**: The alternative to multi-agent sprawl is *not* an unconstrained God-Agent that dumps 1,500 tools into a single prompt. The solution is an **Autonomic Operating System** that executes tasks via a unified state machine with **Demand-Paged Capabilities** and **Mechanical Governance**.

---

## 2. Decision Drivers

* **262,144 Token Baseline Efficiency**: AutoReiv's standard context window baseline is 262,144 tokens (with dynamic compaction). However, local 32B/72B dense models require minimal KV-cache pre-fill latency and lean attention spaces to avoid tool hallucination.
* **Radically Low Cognitive Load**: Operators must not be forced to navigate a 20-agent x 1,500-tool RBAC matrix or guess when to create new agents.
* **Deterministic Guardrails Over "Manager" Agents**: Replace stochastic conversational reviewers with deterministic mechanical checks (linters, AST parsers, exit codes, unit test suites).
* **Self-Governing Evolution**: AutoReiv must monitor its own runtime telemetry and suggest architectural changes (skill splits, daemon promotions) based on mathematical laws rather than human bias.

---

## 3. Considered Options

* **Option 1: Multi-Agent Conversational Roundtable (CARD-340)**: Build multi-agent group chat rooms where personas converse.  
  * *Rejected*: Extreme token drain, lossy handoffs, zero deterministic verification, and persona theater.
* **Option 2: Monolithic God-Agent**: Consolidate everything into a single prompt with all tools loaded globally.  
  * *Rejected*: Crushes KV-cache pre-fill on local models, causes high tool-choice entropy and frequent hallucinations.
* **Option 3: Autonomic Operating System with State-Machine Execution, Demand-Paging, and Mechanical Governance (Chosen)**.

---

## 4. Decision Outcome

Chosen: **Option 3**. We establish the following architectural pillars:

### 1. The 3-Tier Primitive Ontology
* **Tool (Syscall)**: An atomic, typed, executable Python/MCP callable in `ScopedToolRegistry`. Stateless, mechanical, global.
* **Skill (Executable Runbook)**: A procedural Markdown SOP (`SKILL.md`) with YAML frontmatter specifying *how* to sequence tools, declaring dependencies (`requires_tools`), and providing deterministic verification rules.
* **Agent (Security Principal & Service Account)**: A policy scope defining default provider/model, execution trust tier, and sandbox permissions. Agents are created for **blast radius containment and unattended daemons**, not specialized "intelligence".

### 2. Dual-Engine Front Door in Chat Studio
Chat Studio retires persona dropdowns and roundtable selectors in favor of two core channels:
1. **AutoReiv Core**: The primary state-machine orchestrator (`JobPhaseOrchestrator`) executing phased workflows with demand-paged tools and mechanical verification.
2. **Direct Mode**: A raw, unconstrained conversational LLM stream with zero tool schemas, zero overhead, and instant streaming.

### 3. Demand-Paged Capabilities (Slashing the 16k Schema Tax)
* Static prompts receive only 2–4 platform coordination primitives + a compact 1-line Capability Index (< 500 tokens).
* When a task matches a Skill, the runtime host binds the skill's `SKILL.md` and dynamically mounts **only the 2–5 tools declared by that skill**.
* Upon phase completion, verbose tool payloads are compacted; only structured result artifacts enter episodic memory.

### 4. The 5 God-Agent Thresholds
AutoReiv enforces hard mechanical thresholds to prevent God-Agent degradation:
1. **Tool Entropy Limit (Rule of 7)**: No active turn may have > 6–8 tools visible simultaneously.
2. **Context Budget Limit (20% Pre-fill Rule)**: System prompt + tool schemas must never exceed 20% of the active context window.
3. **Security Boundary Collision**: Untrusted external input ingestion (web, email) must never share a turn loop with mutating levers (`cli_exec`, `db_drop`).
4. **Cognitive Conflict**: Self-auditing is forbidden; code generation must be graded by mechanical test runners, not conversational self-critique.
5. **Lifecycle Mismatch**: Interactive chat workflows must never run within the same execution profile as long-running unattended cron daemons.

### 5. The Mechanical Governance Engine & Architectural Telemetry
* **Skill Contract Linter (`autoreiv lint-skills`)**:
  * Enforces `len(requires_tools) <= 6`.
  * Enforces mandatory `verification` clause (command, exit code, assertion).
* **Tool Verification Battery**:
  * Pydantic v2 schemas.
  * Hermetic sandboxed mock unit test (`test_<tool>.py`) required before promotion.
* **Architectural Telemetry Detectors**:
  * Background worker monitors runtime logs for Tool Bloat, Security Collisions, Unattended Routines, and Context Tax.
  * Emits actionable, one-click proposals into the **Architectural Proposals Inbox** in Agent Forge / Observability Studio.

---

## 5. Consequences

### Positive Consequences
* **Immediate Token & Latency Savings**: Prompt schema overhead reduced by >85% (from 16k to <2k tokens), restoring sub-second Time to First Token on local 32B/72B models.
* **Zero Persona Theater**: Eliminates circular conversational chatter and redundant agent-to-agent roundtables.
* **Self-Governing Evolution**: The platform automatically warns operators and drafts refactors when skills become bloated or tasks require dedicated service accounts.
* **Rock-Solid Security**: Untrusted web data is isolated from mutating host commands; raw `cli_exec` is strictly containerized or HITL-gated.

### Negative Consequences / Trade-offs
* **CARD-340 Retirement**: Multi-agent group chat is abandoned as an architectural dead-end.
* **Skill Authoring Rigor**: Skills must now pass the strict mechanical linter before being promoted.

---

## 6. Implementation Plan (Vertical Slices)

1. **[CARD-361]**: Dual-Engine Front Door: AutoReiv Core & Direct Mode (Retire CARD-340 & persona selectors).
2. **[CARD-362]**: Demand-Paged Capability Engine & Progressive Tool Mounting (Prune static 40 tools down to skill-bound sets).
3. **[CARD-363]**: Mechanical Capability Linter & Contract Compiler (`SKILL.md` validation).
4. **[CARD-364]**: Architectural Telemetry & Threshold Detectors (Entropy, Security, Daemons).
5. **[CARD-365]**: Architectural Proposal Inbox in Agent Forge Studio.
