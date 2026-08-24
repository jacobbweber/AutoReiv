# ADR-0003: Agent Kernel Scoped Tool Registry and SQLite State Persistence

> **Date**: 2026-08-22  
> **Status**: Accepted  
> **Deciders**: Human Visionary, AI Agent (Antigravity)  
> **Consulted**: `script-to-agent-labs` Reference Bank (Tiers 2, 3, 5, 6)

---

## 1. Context & Problem Statement

AutoReiv requires autonomous agents that:
1. Execute multi-turn ReAct decision loops with tool calls.
2. Maintain strict tool access boundaries (e.g. Linux Sysadmin can run CLI tools, but Librarian or General Assistant cannot unless explicitly authorized).
3. Persist conversation history and session states isolated per agent and session across system restarts.
4. Collect comprehensive telemetry for every agent turn, tool execution, token usage, and error rate.

We must establish the execution harness, RBAC tool permissions, database persistence, and observability telemetry.

---

## 2. Decision Drivers

* **Role-Based Access Control (RBAC)**: Tools must be scoped per agent profile to prevent unintended execution or privilege escalation.
* **Zero External DB Overhead**: SQLite in WAL mode provides zero-config, single-file embedded database storage suitable for bare-metal, systemd, and Docker deployments without needing a separate Postgres/MySQL container.
* **Deterministic Loop Controls**: Explicit turn budgets and cycle detection prevent runaway token costs and infinite tool recursion.
* **Observable Telemetry**: Telemetry spans must capture latency, prompt/completion tokens, and tool errors out of the box.

---

## 3. Considered Options

* **Option 1**: In-memory state only without persistence.
* **Option 2**: Heavy multi-service stack (PostgreSQL + Redis + OpenTelemetry Collector).
* **Option 3 (Recommended)**: Embedded SQLite (WAL mode) with an async state store, pure Python ReAct Agent Kernel, Scoped Tool Registry, and internal Telemetry Collector.

---

## 4. Decision Outcome

Chosen option: **Option 3 (Embedded SQLite + Scoped Tool Registry + ReAct Kernel)**, because:
- It requires zero background daemon setup, perfectly supporting lightweight deployment on the Nimo Mini PC (Ubuntu), Windows, or single-container Docker.
- SQLite WAL mode easily handles hundreds of concurrent read/write operations per second.
- It builds directly on the clean patterns demonstrated in `script-to-agent-labs` (`03_the_dispatcher`, `04_the_loop`, `05_the_budget`, `07_the_state`, `16_the_shield`).

### Positive Consequences
* Zero database setup or migration infrastructure dependencies.
* High performance, local-first conversation checkpoints.
* Complete isolation: agents only see and execute tools assigned in their manifest.
* Full traceability and telemetry recorded into SQLite for KPI dashboards.

### Negative Consequences / Trade-offs
* For multi-node distributed clusters in the far future, SQLite would require LiteFS or Postgres adapter (cleanly abstracted via Ports & Adapters).
