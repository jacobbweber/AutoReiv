# [CARD-176] Agent Training Factory Deliverables Taxonomy: MCP Servers, Atomic Tools, and Runbooks

> **Status**: Ready
> **Created**: 2026-09-06
> **Spec Reference**: docs/specs/agent-pack-factory/; docs/adr/ (future ADR for MCP vs Native Tools)
> **Labels**: `type:architecture`, `type:spec`, `AutoReiv.Orchestration`, `AutoReiv.Packs`, `AutoReiv.MCP`

---

## 1. Why / Intent

During capability creation for agents like Hyper-V and Personal Finance, Jacob made a key architectural realization:
- Writing dozens of ad-hoc PowerShell or host scripts directly inside agent packs can become brittle and cluttered.
- For system and external infrastructure management (e.g., Hyper-V virtualization, Docker, cloud APIs, network gear), having the Agent Training Factory author a **standard Model Context Protocol (MCP) Server** provides clean process isolation, standard protocol transport (stdio/SSE), reusable schemas, and eliminates host environment command pollution.
- For internal, pack-local data operations (such as Personal Finance querying its private `<agent>_storage.db` SQLite database), **atomic in-process Python tools** are lightweight, zero-overhead, and ideal.
- In both cases, **Skills (`SKILL.md`)** remain the high-level runbook explaining when and how the agent invokes those capabilities.

This card establishes the evaluation criteria, architectural boundaries, and authoring templates for ATF deliverables across **MCP Servers**, **Atomic Tools**, and **Skill Runbooks**.

---

## 2. Deliverable Selection Criteria

| Domain / Capability Type | Recommended Deliverable | Why It Fits | Example |
| :--- | :--- | :--- | :--- |
| **System & Infrastructure** | **Agent Pack MCP Server** | Sandboxed process boundary; reusable tool definitions; eliminates PowerShell cmdlet collisions on the host. | Hyper-V Manager, Docker Controller, Proxmox API |
| **Pack-Private Local Data** | **Atomic Python Tools** | Fast in-process execution; direct SQLite connection; zero subprocess overhead or server management. | Personal Finance Ledger, Task Tracker |
| **Procedural Knowledge & SOP** | **Skill Runbooks (`SKILL.md`)** | Markdown runbooks loaded into context that teach the agent when and how to call tools/MCP servers. | Autounattend VM setup procedure, Monthly Budget Reconciliation |

---

## 3. What Jacob Sees & Controls (UI / UX)

### Train Agent Handshake Modal:
- **Deliverable Architecture Option** (advanced toggle):
  - `Deliverable Type`:
    - `Auto-Detect based on Intent` [Default]
    - `MCP Server (Isolated System Process)`
    - `Native Python Tools (In-Process)`
- The Blueprint phase classifies the domain and declares the deliverable type in its packet facts.

### Agent Studio:
- Under Card 5 (Tools & Capabilities):
  - Displays whether each capability is backed by a **Native Pack Tool** (`tools/*.py`) or an **Agent MCP Server** (`mcp/server.py`).

---

## 4. Acceptance Criteria

- [ ] [REQ-DELIV-001] Architectural Decision Record (ADR) published documenting MCP Server vs. Native Python Tool decision matrix.
- [ ] [REQ-DELIV-002] Agent Training Factory Blueprint phase enhanced to classify deliverable type (`mcp` vs `native_tool`).
- [ ] [REQ-DELIV-003] Author phase equipped with standardized MCP server scaffold template for infrastructure domains.
- [ ] [REQ-DELIV-004] Pack manifest (`pack.json`) extended to support declared agent-scoped MCP servers alongside native tools.
- [ ] [REQ-DELIV-005] Zero test regressions across existing tool synthesis and verification batteries.

---

## 5. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Do not dismantle working native tools (e.g. Finance SQLite tools) that already function well.
- Work strictly on local `qa` branch.
