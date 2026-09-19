# Requirements: Lean JIT Agent Discovery and Isolated Subagent Handoff Engine

> **Standard**: AWS Kiro EARS (Easy Approach to Requirements Syntax)  
> **Traceability Prefix**: `[REQ-ORCH-xxx]`  
> **Target Components**: `AutoReiv.Orchestration`, `AutoReiv.Kernel`, `AutoReiv.Skills`, `AutoReiv.Web`

---

## 1. System Context & User Stories

As an **Operator & AI Systems Architect**,  
I want **agents to dynamically discover peer capabilities on demand and execute isolated subagent handoffs without pre-loading full fleet manifests into system prompts**,  
And I want **handoffs to execute in private child execution loops with strict recursion guardrails and clean result synthesis**,  
So that **AutoReiv operates with maximum token efficiency, near-zero context bloat, and ultra-high reliability on models ranging from 1B-8B local LLMs to frontier cloud APIs**.

---

## 2. EARS Requirements Specification

### [REQ-ORCH-001]: Just-In-Time (JIT) Agent Directory Indexer
- **Type**: Ubiquitous
- **Statement**: The system shall provide an `AgentDirectoryService` that indexes all active built-in agent profiles and custom SQLite agents by capability keywords, specialization summaries, and assigned skill tags, returning ranked, token-compact Agent Cards without injecting static rosters into base system prompts.

### [REQ-ORCH-002]: Ultralight Orchestration Skill Primitives
- **Type**: Ubiquitous
- **Statement**: The system shall provide an `OrchestrationSkill` pack exposing two lean atomic tools: `lookup_agents(query: str, limit: int = 3)` returning compact agent capability summaries (<60 tokens), and `handoff_to_agent(target_agent_id: str, task_directive: str, input_payload: dict = {})` adhering to strict schema contracts.

### [REQ-ORCH-003]: Isolated Context Execution & Anti-Recursion Guardrail
- **Type**: Event-Driven
- **Statement**: When `handoff_to_agent` is invoked, the `HandoffIsolationEngine` shall instantiate an isolated execution loop with a clean 0-turn context, bound execution to max turns (default 5, bounded 1–10), enforce a max recursion depth of 2 tiers, and reject circular self-handoffs (`target_agent_id == caller_agent_id`).

### [REQ-ORCH-004]: Real-Time Handoff Telemetry & UI Affordance
- **Type**: Event-Driven
- **Statement**: When an agent executes a handoff during Chat Studio SSE streaming, the kernel shall emit `handoff_start` and `handoff_complete` events, and the web interface shall render an expandable subagent execution pill displaying the target agent name, turns elapsed, and execution outcome.
