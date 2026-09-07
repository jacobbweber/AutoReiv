# [CARD-183] Per-Agent Remote MCP Server Configuration and Agent Studio Inspector

> **Status**: Done
> **Created**: 2026-09-07
> **Spec Reference**: docs/specs/mcp-per-agent/
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Agents`, `AutoReiv.Infrastructure`, `AutoReiv.Packs`

---

## 1. Why / Intent

1. **Remote MCP Server Principle**: MCP servers should not be assumed to be local python subprocesses tied to AutoReiv's internal filesystem. Modern and best-practice MCP architecture treats MCP servers as independent, network-accessible remote services (running on external hosts, in Docker containers, or in cloud environments).
2. **Per-Agent Scoping**: Previously, MCP servers were registered in Global Settings, making tool access global and unclear. Each agent should own or declare which MCP servers it communicates with. If an agent pack defines an MCP server, it lives in the agent's pack schema (`pack.json`) and profile (`AgentProfile`), allowing per-agent configuration, inspection, and testing directly in Agent Studio.
3. **Agent Studio Visibility**: Operators need to see, configure, test, and scope MCP servers directly in Agent Studio (`Agent Forge`) without switching to global settings.

---

## 2. What to Build

### A. Domain & Schema Updates
1. **`AgentProfile` (`src/domain/agents/profiles.py`)**:
   - Add `mcp_servers: List[MCPServerConfig] = Field(default_factory=list)` to `AgentProfile`.
   - Support both remote HTTP/SSE endpoints (`url`, `transport: "sse"`) and command-based configurations (`command`, `transport: "stdio"`).
2. **`AgentPackManifest` (`src/application/agent_packs/schema.py`)**:
   - Align `mcp_server` and `mcp_servers` in pack schema.
   - Support remote server definitions with URL, transport, and environment/header auth.

### B. Remote SSE Client Adapter (`src/infrastructure/mcp/client_adapter.py`)
- Enhance `MCPClientAdapter` to support remote HTTP/SSE endpoints (`transport="sse"`, `url="http://..."`):
   - In addition to stdio `subprocess.Popen`, support connecting to remote MCP servers via HTTP/SSE.
   - Discovers tools via remote `tools/list` JSON-RPC over HTTP/SSE.
   - Dispatches tool invocations via remote `tools/call` JSON-RPC over HTTP/SSE.

### C. Backend API Endpoints (`src/web/routers/agents.py` & `src/web/routers/mcp.py`)
- `GET /api/agents/{agent_id}/mcp`: List MCP servers configured for this agent with live mount/connection status and discovered tools.
- `POST /api/agents/{agent_id}/mcp`: Add or update an MCP server configuration for this agent (saves to agent profile and pack manifest).
- `DELETE /api/agents/{agent_id}/mcp/{server_name}`: Remove an MCP server from this agent.
- `POST /api/agents/{agent_id}/mcp/test`: Probe a remote or local MCP server for this agent and return latency and discovered tools.

### D. Frontend: Agent Studio Inspector (`src/web/templates/index.html` & `src/web/static/modules/studios/forge.js`)
1. **Agent Studio MCP Section (`#forgeMcpServersCard`)**:
   - Dedicated card inside Agent Studio for the selected agent.
   - Lists active MCP server connections for the agent with status indicators (Mounted/Connected, Tool Count).
   - "Add Remote MCP Server" form: Name, Transport (`SSE (Remote)` / `Command (Local)`), URL / Endpoint, Headers / Auth.
   - "Test Connection" button with live feedback showing discovered tools and response latency.
2. **Tool Scoping Integration**:
   - Discovered tools from the agent's MCP servers automatically surface in the agent's tools grid with `[MCP Server]` badge and are scoped to this agent.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] **[REQ-MCP-AGENT-001]**: `AgentProfile` and `AgentPackManifest` support per-agent `mcp_servers` list with remote SSE URL and transport specifications.
- [x] **[REQ-MCP-AGENT-002]**: `MCPClientAdapter` connects to remote MCP HTTP/SSE endpoints, supporting tool discovery (`tools/list`) and execution (`tools/call`).
- [x] **[REQ-MCP-AGENT-003]**: Agent Studio (`Agent Forge`) displays the per-agent MCP servers card (`#forgeMcpServersCard`), allowing operators to view, add, delete, and test remote MCP servers for the selected agent.
- [x] **[REQ-MCP-AGENT-004]**: Agent turn execution correctly invokes the agent's scoped remote MCP tools through `ScopedToolRegistry`.
- [x] **[REQ-MCP-AGENT-005]**: Automated tests pass: Vitest for Agent Studio MCP UI controls, Pytest for per-agent schema, remote adapter, and API endpoints.

---

## 4. UI Wireframe

```text
+--------------------------------------------------------------------------+
| 🌐 Remote MCP Servers                                 [+ Add MCP Server] |
+--------------------------------------------------------------------------+
|  hyperv-service (Remote SSE)                                  🟢 Connected|
|  URL: http://192.168.1.50:8080/sse                              3 tools  |
|  [⚡ Test Connection] [🗑️ Remove]                                        |
|  Tools: manage_hyperv_vm, manage_hyperv_network, manage_hyperv_template  |
+--------------------------------------------------------------------------+
```
