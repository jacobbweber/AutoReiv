# [CARD-176] Agent Training Factory Deliverables Taxonomy: MCP Servers, Atomic Tools, and Runbooks

> **Status**: In Review
> **Created**: 2026-09-06
> **Updated**: 2026-09-07 (Implemented full MCP server framework, UI taxonomy controls, and subprocess battery)
> **Spec Reference**: docs/specs/agent-pack-factory/; docs/adr/0049-mcp-servers-vs-native-tools-deliverable-taxonomy.md
> **Labels**: `type:architecture`, `type:spec`, `AutoReiv.Orchestration`, `AutoReiv.Packs`, `AutoReiv.MCP`, `AutoReiv.Skills`

---

## 1. Why / Intent

During capability creation for agents like Hyper-V and Personal Finance, Jacob made a key architectural realization:
- Writing dozens of ad-hoc PowerShell or host scripts directly inside agent packs becomes brittle, cluttered, and causes command collisions (e.g. VMware PowerCLI intercepting Hyper-V cmdlets).
- For system and external infrastructure management (e.g., Hyper-V virtualization, Docker, cloud APIs, network gear), having the Agent Training Factory author a **standard Model Context Protocol (MCP) Server** provides clean process isolation, standard JSON-RPC 2.0 protocol transport (stdio), reusable schemas, and eliminates host environment command pollution.
- For internal, pack-local data operations (such as Personal Finance querying its private `<agent>_storage.db` SQLite database), **atomic in-process Python tools** are lightweight, zero-overhead, and ideal.
- In both cases, **Skills (`SKILL.md`)** remain the high-level runbooks explaining when and how the agent invokes those capabilities, following industry standards (YAML trigger frontmatter, progressive disclosure, and imperative step-by-step SOPs).

This card establishes the evaluation criteria, architectural boundaries, reusable server framework, UI controls, and authoring templates for ATF deliverables across **MCP Servers**, **Atomic Tools**, and **Skill Runbooks**.

---

## 2. Deliverable Selection Criteria

| Domain / Capability Type | Recommended Deliverable | Why It Fits | Example |
| :--- | :--- | :--- | :--- |
| **System & Infrastructure** | **Agent Pack MCP Server** | Sandboxed process boundary; reusable tool definitions; eliminates PowerShell cmdlet collisions on the host. | Hyper-V Manager, Docker Controller, Proxmox API |
| **Pack-Private Local Data** | **Atomic Python Tools** | Fast in-process execution; direct SQLite connection; zero subprocess overhead or server management. | Personal Finance Ledger, Task Tracker |
| **Procedural Knowledge & SOP** | **Skill Runbooks (`SKILL.md`)** | Markdown runbooks loaded into context that teach the agent when and how to call tools/MCP servers. | Autounattend VM setup procedure, Monthly Budget Reconciliation |

---

## 3. Reusable Pack MCP Server Framework

AutoReiv provides a lightweight, zero-dependency Python MCP server micro-framework at `src/infrastructure/mcp/pack_server.py`:
- Standard JSON-RPC 2.0 protocol over `stdio`.
- Declarative tool registration: `@server.tool(name="...", description="...")`.
- Standard lifecycle handling: `initialize`, `tools/list`, `tools/call`, and shutdown.
- Standard pack folder layout:
  ```text
  packs/<agent_id>/
    ├── pack.json
    ├── mcp/
    │   ├── server.py        <-- Standalone executable MCP server
    │   └── handlers/        <-- Domain tool implementations
    └── skills/
        └── <skill_id>/SKILL.md
  ```
- Pack manifest declaration (`pack.json`):
  ```json
  "mcp_server": {
    "enabled": true,
    "entrypoint": "mcp/server.py",
    "transport": "stdio"
  }
  ```
- Dynamic auto-mount: When an agent is loaded or active in Chat, `MCPClientManager` automatically starts and monitors the pack's MCP server subprocess, mounting its tools into `ScopedToolRegistry`.

---

## 4. Skill Runbook Standard (`SKILL.md`)

Authored skill runbooks adhere to the open Agent Skills specification:
1. **Trigger-Rich YAML Frontmatter**:
   ```yaml
   ---
   name: hyperv-vm-lifecycle
   description: "Use when creating, starting, stopping, checkpointing, or inspecting Hyper-V virtual machines. Triggers on VM management, health inspection, or snapshot requests."
   ---
   ```
2. **Progressive Disclosure**:
   - Level 1: System prompt turn loads only `name` and `description` (tiny context footprint).
   - Level 2: Agent dynamically loads the full runbook when triggered.
3. **Structured Imperative SOP Sections**:
   - **Purpose & Scope**: Explicit statement of what the skill does and does not do.
   - **Prerequisites & Tool Mapping**: Tools required (MCP or native) and required host permissions.
   - **Standard Operating Procedure (SOP)**: Numbered steps: Pre-flight check -> Input validation -> Execution -> Post-verification.
   - **Safety & Guardrails**: Destructive actions requiring human confirmation.
   - **Error Handling & Recovery**: Known failure modes and exact recovery actions.

---

## 5. What Jacob Sees & Controls (UI / UX)

### Train Agent Handshake Modal (`#trainAgentHandshakeModal`):
- **Deliverable Architecture Option**:
  - `Auto-Detect (Recommended)` [Default]
  - `MCP Server (Isolated Process)`
  - `Native Python Tools (In-Process)`
- **Advanced Requirements & Boundaries (Collapsible Accordion)**:
  - `Operational Constraints & Boundaries`: Text input for safety rules, read-only defaults, confirmation gates.
  - `Host Environment & Prerequisites`: Text input for required OS roles, modules, or sockets.
  - `Reference Documentation & Snippets`: Area to paste official cmdlet syntax, docs, or API endpoints.

### Agent Studio:
- Under Agent Pack Skills & Tools (`#forgePackBox`):
  - Displays whether each capability is backed by a **Native Tool** (`tools/*.py`) or an **Agent MCP Server** (`mcp/server.py`).

---

## 6. Acceptance Criteria

- [ ] [REQ-DELIV-001] Architectural Decision Record (ADR 0049) published documenting MCP Server vs. Native Python Tool decision matrix and pack layout.
- [ ] [REQ-DELIV-002] Lightweight pack MCP server base class implemented at `src/infrastructure/mcp/pack_server.py`.
- [ ] [REQ-DELIV-003] Train Agent Handshake Modal (`#trainAgentHandshakeModal`) equipped with Deliverable Architecture selector and Requirements & Boundaries inputs.
- [ ] [REQ-DELIV-004] Intent Distill and Blueprint phases enhanced to ingest structured requirements and classify deliverable type (`mcp` vs `native_tool`).
- [ ] [REQ-DELIV-005] Author phase equipped with standardized MCP server scaffold template and enhanced `SKILL.md` authoring rubric (trigger frontmatter + imperative SOP).
- [ ] [REQ-DELIV-006] Verify phase equipped with subprocess JSON-RPC verification harness for MCP server deliverables.
- [ ] [REQ-DELIV-007] Promote phase and pack manifest (`pack.json`) extended to support declared agent-scoped MCP servers.
- [ ] [REQ-DELIV-008] Zero test regressions across existing tool synthesis and verification batteries.

---

## 7. Constraints & Working Agreement

- **Ready card only. Do not implement until Jacob explicitly says build.**
- Do not dismantle working native tools (e.g. Finance SQLite tools) that already function well.
- Work strictly on local `qa` branch.
