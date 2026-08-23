# ADR-0021: Lean Just-In-Time (JIT) Agent Discovery and Isolated Subagent Handoff Engine

> **Status**: Accepted  
> **Date**: 2026-08-23  
> **Decision Makers**: Jacob Weber, Principal Agent Engineer  
> **Linked Issue / Card**: CARD-020

---

## 1. Context and Problem Statement

Multi-agent coordination requires agents to know when and how to delegate subtasks to peer agents.
However, pre-loading entire fleet rosters, tool schemas, and capabilities into every agent's base system prompt consumes 1,500–4,000 tokens on turn 0, causing severe context degradation and hallucination on small (1B–8B) local models.
We need an ultra-efficient, token-lean coordination architecture that works reliably across both local models and frontier APIs.

---

## 2. Considered Options

- **Option A: Static Prompt Injected Rosters**:
  Inject full agent rosters and capabilities directly into all system prompts.
- **Option B: Dynamic JIT Capability Lookup + Isolated Handoff Engine (Chosen)**:
  Provide two lightweight atomic tools (`lookup_agents`, `handoff_to_agent`). Agents discover capabilities on demand and execute handoffs in clean, isolated child loops with recursion limits.

---

## 3. Decision Outcome

**Chosen Option**: **Option B**.

### Positive Consequences
- **Zero Turn-0 Prompt Bloat**: Base system prompts stay under 350 tokens.
- **No Context Leakage**: Subagents execute with clean, task-isolated context.
- **Robust Local Model Compatibility**: 1B–8B local LLMs run without attention saturation or schema confusion.
- **Deterministic Safety**: Bounded turn limits (<=5), max recursion depth of 2, and self-handoff prevention.
