---
id: CARD-392
title: "AutoReiv Hosted MCP Server and Cross-Instance Federation"
status: Ready
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:mcp
  - domain:federation
  - area:api
  - area:infrastructure
---

# [CARD-392] AutoReiv Hosted MCP Server and Cross-Instance Federation

> **Status**: Ready  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:mcp`, `domain:federation`, `area:api`, `area:infrastructure`  

---

## 1. Why / Intent (Beat 1)

Currently, AutoReiv operates strictly as an **MCP Client**, connecting outward to external MCP servers. Operators need AutoReiv to also act as a **Hosted MCP Server**, exposing its rich internal capabilities (Wiki notes, knowledge graph, system diagnostics, project inspection, routine triggers) outward over standard HTTP/SSE.

This enables two transformative workflows:
1. **External AI Client Integration**: Tools like Claude Desktop, Cursor, and Windsurf can connect to `http://localhost:8000/api/mcp/sse` to query AutoReiv's local Wiki and invoke local tools.
2. **AutoReiv-to-AutoReiv Federation (Multi-Instance)**: A developer workstation or laptop instance can connect to a 24/7 dedicated Homelab instance as an MCP server. The workstation discovers the homelab's specialized tools (VM control, Docker management, local hardware) and automatically authors a companion `SKILL.md` runbook, allowing agents to coordinate across physical machines using the open MCP standard without proprietary networking plumbing.

**In-Process Invariant**: Local agents on the same instance always execute tools directly in-process (0.1ms latency). MCP is reserved strictly for crossing external host boundaries.

---

## 2. What AutoReiv Does Now (Beat 2)

1. AutoReiv has an MCP client adapter (`MCPClientManager` in `src/infrastructure/mcp/`), but has zero inbound MCP server endpoints.
2. External AI tools cannot access AutoReiv's knowledge vault or tools via MCP.
3. Multiple AutoReiv instances (e.g. laptop and homelab server) run in complete isolation with no standard mechanism to share or delegate tools.

---

## 3. What Will Change (Beat 3)

1. **FastAPI Hosted MCP Server Endpoint (`/api/mcp/sse`)**:
   - Implement official MCP SSE protocol endpoints on the main port (8000):
     - `GET /api/mcp/sse`: Server-Sent Events stream for connection handshake and notifications.
     - `POST /api/mcp/messages`: JSON-RPC 2.0 endpoint handling `initialize`, `tools/list`, and `tools/call`.
   - Readily exposes registered tools from `ScopedToolRegistry` (Wiki tools, system info, agent dispatch).
   - Optional API Key / Bearer token authentication configured in Settings Studio.
2. **AutoReiv-to-AutoReiv Federation Client Workflow**:
   - In Settings Studio (`#view-settings`), operators can add a peer AutoReiv instance URL (`http://<remote-host>:8000/api/mcp/sse`).
   - The local client connects, discovers the remote tools, namespaces them (e.g. `mcp_homelab_*`), and auto-scaffolds a companion `SKILL.md` runbook (`skills/homelab-cluster/SKILL.md`).
3. **Strict In-Process Local Execution**:
   - Verify that local turn execution routes through direct in-process Python callables in `tool_registry.py` and never routes through the loopback HTTP MCP endpoint.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire ad-hoc custom curl/HTTP scripts for cross-machine coordination.
- Eliminate the one-way limitation where AutoReiv could only consume, but never provide, MCP capabilities.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-392-001] (Ubiquitous)**: THE SYSTEM SHALL expose an inbound Model Context Protocol (MCP) server endpoint at `/api/mcp/sse` over HTTP with Server-Sent Events on the primary web port.
- **[REQ-392-002] (Event-Driven)**: WHEN an external MCP client (or peer AutoReiv instance) sends a `tools/list` JSON-RPC request to `/api/mcp/messages`, THE SYSTEM SHALL return the schemas of all authorized tools.
- **[REQ-392-003] (Event-Driven)**: WHEN an external client sends a `tools/call` request, THE SYSTEM SHALL execute the tool in `ScopedToolRegistry` and stream the structured result back to the client.
- **[REQ-392-004] (State-Driven)**: WHILE connecting to a peer AutoReiv instance via Settings Studio, THE SYSTEM SHALL successfully handshake via SSE, mount the remote tools, and author a companion `SKILL.md` runbook.
- **[REQ-392-005] (Negative Assertion)**: Automated tests shall explicitly assert that local agent turns execute tools directly in-process without generating HTTP network requests to `/api/mcp/sse`.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-392-autoreiv-hosted-mcp-server` cut from `qa`.
- Unit and integration tests:
  - `tests/unit/mcp/test_hosted_mcp_server.py` (JSON-RPC handshake, tools/list, tools/call).
  - `tests/integration/test_autoreiv_federation_e2e.py` (Client-to-Server loopback proof).
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/sdd-workflow/scripts/preflight.py`.
