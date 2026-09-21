---
id: CARD-392
title: "AutoReiv Hosted MCP Server and Cross-Instance Federation"
status: Done
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

> **Status**: Done  
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

1. **FastAPI Hosted MCP Server Endpoints (`/api/mcp/sse`, `/api/mcp/messages`)**:
   - Implement the official MCP SSE transport on the main application port (8000):
     - `GET /api/mcp/sse`: Server-Sent Events stream for connection handshake, session initialization, and notifications.
     - `POST /api/mcp/messages`: JSON-RPC 2.0 endpoint handling `initialize`, `tools/list`, and `tools/call`.
2. **Agent-Mediated Capability Publishing (Zero Naked Tool Leakage)**:
   - Dynamic Agent Dispatch Tools: Expose active chat-visible agents as high-level tools (`ask_developer`, `ask_autoreiv`, `ask_tutor`, etc.). When invoked, AutoReiv runs the agent's turn via `AgentKernel.execute_turn` with full `AGENTS.md` governance, skill runbooks, and tool guardrails, returning the final scrubbed markdown deliverable.
   - Safe Passive Lookups: Expose read-only knowledge vault lookup tools (`search_wiki`, `read_wiki_document`) for immediate passive retrieval without spinning up a full agent turn.
   - Optional API Key / Bearer token authentication configured in Settings Studio.
3. **AutoReiv-to-AutoReiv Federation Workflow**:
   - In Settings Studio (`#view-settings`), operators can configure a peer AutoReiv instance endpoint (`http://<remote-host>:8000/api/mcp/sse`).
   - The local client connects, discovers the remote agent tools (e.g. `mcp_homelab_ask_developer`), and auto-mounts them through a companion skill runbook (`skills/homelab-cluster/SKILL.md`), keeping tool usage strictly governed.
4. **Strict In-Process Local Execution Invariant**:
   - Verify that local turn execution routes through direct in-process Python callables in `tool_registry.py` and never loops through the HTTP MCP endpoint.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire ad-hoc custom curl/HTTP scripts for cross-machine coordination.
- Eliminate raw naked tool publishing over remote interfaces that bypass agent runbooks and SOPs.
- Eliminate the one-way limitation where AutoReiv could only consume, but never provide, MCP capabilities.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-392-001] (Ubiquitous)**: THE SYSTEM SHALL expose an inbound Model Context Protocol (MCP) server endpoint at `/api/mcp/sse` over HTTP with Server-Sent Events on the primary web port.
- **[REQ-392-002] (Event-Driven)**: WHEN an external MCP client (or peer AutoReiv instance) sends a `tools/list` JSON-RPC request to `/api/mcp/messages`, THE SYSTEM SHALL return schemas for agent dispatchers (`ask_<agent_id>`) and safe passive wiki lookups.
- **[REQ-392-003] (Event-Driven)**: WHEN an external client sends a `tools/call` request for an agent dispatcher (e.g. `ask_developer`), THE SYSTEM SHALL execute an autonomous turn via `AgentKernel.execute_turn` and return the structured response.
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
