# ADR-0048: Autonomous Agent Pack Factory and Self-Testing Capability Loop

> **Date**: 2026-09-05  
> **Status**: Accepted  
> **Deciders**: Jacob Weber, Antigravity Agent  
> **Consulted**: AutoReiv Core Architecture  

---

## 1. Context & Problem Statement
Users want AutoReiv to autonomously create, train, test, and optimize new specialist agents (e.g. Linux Game Server Host, Personal Finance, HomeLab Sysadmin) without requiring manual Python coding, schema design, or prompt engineering. Furthermore, users operating substantial local hardware (e.g. 128GB unified memory running local Ollama 32B/72B models) have free, continuous capacity for overnight execution.

Existing agentic architectures often suffer from two major flaws:
1. **Unconstrained God Agents**: Giving a single agent file-editing, command execution, and architecture planning tools leads to massive prompt bloat, high confusion rates, and hallucinations on local models.
2. **On-the-Fly Tool Inventions in Live Chats**: Generating ad-hoc tools in live conversation loops without deterministic evaluation yields broken scripts, insecure commands, and unmaintainable sprawl.

---

## 2. Decision Drivers
* **Strict Pack Isolation**: All authored tools, runbooks, and definitions must be written strictly inside self-contained User Agent Packs (`$DATA_DIR/packs/<agent_id>/`) to preserve complete portability.
* **Separation of Roles**: The factory must use dedicated platform specialist packs (`conductor`, `inspector`, `coder`, `sandbox_runner`, `critic`) with tightly scoped toolsets and `show_in_chat: false`.
* **Zero Hallucinations via 4-Stage Verification**: Newly authored tools must pass deterministic exit code checks, safety guardrails, idempotency stress tests, and an SRE Critic code audit before registration.
* **Anti-Bloat & Split Policies**: Automatically consolidate micro-tools into verb-action dispatchers (3–6 tools max) and split multi-domain sprawl into separate agent packs.
* **Zero Cloud / Vector DB Dependencies**: 100% pure local Python standard library and SQLite WAL on Windows.

---

## 3. Considered Options
* **Option 1**: Single monolithic Conductor agent that plans, codes, executes, and evaluates in one turn loop.
* **Option 2**: Dynamic code generation directly in live chat turns without isolated sandbox testing.
* **Option 3**: The Catalog-Factory-in-a-Lab architecture featuring 5 dedicated Platform Factory packs, typed SQLite packet interchange, conditional graph orchestration, and an exhaustive 4-stage verification battery (Chosen).

---

## 4. Decision Outcome
Chosen option: **Option 3**, because:
1. It eliminates the "god agent" anti-pattern: each factory agent has a razor-sharp prompt and only 2–3 tools, minimizing context usage and hallucinations on local Ollama models.
2. It guarantees safety: live systems are only probed with read-only tools; all tool development and mutation testing occurs inside local sandboxes (`EphemeralSandbox`).
3. It keeps User Agent Packs clean and portable: tools belong directly to the pack being trained, so export `.zip` archives work anywhere.
4. It enables true overnight unattended execution: progress is tracked durably in SQLite and resumes cleanly across restarts.

### Positive Consequences
* High reliability: 4-stage verification battery prevents broken tools from entering agent packs.
* Zero tool bloat: Consolidation rules prevent micro-tool proliferation.
* Non-technical friendly: 30-second Socratic handshake replaces complex technical requirements authoring.

### Negative Consequences / Trade-offs
* Overnight execution requires multi-turn loop compute; mitigated by running locally on free unified memory hardware.

---

## 5. Pros and Cons of Options

### Option 1: Monolithic Conductor Agent
* Good: Fewer agent definitions to manage.
* Bad: Overwhelms local model context windows with tool schemas; high hallucination and failure rates.

### Option 2: Live Chat On-The-Fly Generation
* Good: Instantaneous generation without overnight wait.
* Bad: High risk of runtime crashes, syntax errors, and destructive commands executed on live user systems.

### Option 3: Dedicated Factory Team with 4-Stage Sandbox Battery
* Good: Battle-tested correctness, strict pack isolation, anti-bloat consolidation, safe overnight autonomy.
* Bad: Requires multi-phase graph orchestrator and sandbox mock management.
