# ADR-0004: Built-in Agent Manifests and Standard Scoped Skills

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 3, 5, 6)

---

## 1. Context & Problem Statement

AutoReiv requires out-of-the-box specialization for 4 distinct operational domains:
1. **General Assistant**: Daily workflow and task tracker.
2. **Linux Sysadmin**: Host server maintenance and hardware metrics.
3. **Librarian**: Markdown document authoring and YAML frontmatter indexing for the PARA-Wiki knowledge base.
4. **System Agent**: Internal platform health and telemetry analysis.

We must define their profiles and build hermetic, testable skill implementations that enforce least-privilege security.

---

## 2. Decision Drivers

* **Least-Privilege Isolation**: Each skill must be bound only to authorized agent profiles.
* **Hermetic & Cross-Platform**: System inspection and file writing must operate cleanly across Linux (Ubuntu Nimo PC), Windows, and Docker without crashing on platform-specific discrepancies.
* **Path-Jailing for Wiki Operations**: Any file operation performed by the Librarian must be strictly validated to prevent path traversal outside the designated Wiki root directory.

---

## 3. Considered Options

* **Option 1**: Monolithic tool suite with all tools available to all agents.
* **Option 2**: Dynamic code generation per agent without predefined manifests.
* **Option 3 (Recommended)**: Explicit `AgentProfile` constants paired with modular `Skill` classes registered via `BuiltinAgentRegistry` into `ScopedToolRegistry`.

---

## 4. Decision Outcome

Chosen option: **Option 3 (Explicit Profiles & Modular Scoped Skills)**, because:
- It enforces strict RBAC security and prevents hallucinations where an assistant might accidentally trigger a bash script.
- It makes every skill unit-testable in isolation.
- It gives the user immediate out-of-the-box utility on Day 1.

### Positive Consequences
* Clear separation of duties across the 4 agents.
* Safe path-jailed file operations for Wiki management.
* Out-of-the-box telemetry inspection and system diagnostics.
