# Requirements Specification: MCP Environment Variables, Live Tool Discovery Preview, and Agent Forge Pack Binding

## 1. System Intent & Scope
Enable robust, production-grade MCP server integration within AutoReiv by providing:
1. Secure key-value environment variables per server for external authentication tokens and database URLs.
2. Live diagnostic connection testing and tool discovery preview prior to mounting.
3. Dynamic MCP skill pack binding within Agent Forge Studio with granular per-agent permission toggling.

---

## 2. EARS Requirements Matrix

### [REQ-MCP-007] MCP Server Secure Environment Variables Key-Value Persistence & Process Injection
- **Type**: Ubiquitous
- **Description**: The AutoReiv Control Plane SHALL persist key-value environment variables associated with each configured MCP server in SQLite settings and inject them into the subprocess environment during `MCPClientAdapter` initialization.
- **Acceptance Criteria**:
  1. `MCPServerConfig` accepts an optional `env: Dict[str, str]` dictionary mapping environment variable names to string values.
  2. When spawning an MCP server subprocess via `asyncio.create_subprocess_exec`, `MCPClientAdapter` combines the host OS environment with the configured `env` variables, prioritizing the server-specific overrides.
  3. Environment variables are retained through server updates and app restarts.

### [REQ-MCP-008] Live MCP Handshake & Tool Discovery Diagnostic Endpoint
- **Type**: Event-Driven
- **Description**: When a client issues a `POST /api/settings/mcp/test` request with a candidate MCP server configuration, the backend SHALL execute a temporary stdio JSON-RPC handshake, query `tools/list`, and return the discovered tool definitions and roundtrip latency without modifying persistent settings.
- **Acceptance Criteria**:
  1. The endpoint accepts `MCPServerConfig` payload with `name`, `command`, and optional `env`.
  2. The endpoint spawns a transient `MCPClientAdapter`, invokes `list_tools()`, measures execution time in milliseconds, terminates the subprocess, and returns `{"status": "ok", "latency_ms": float, "tools_count": int, "tools": List[ToolDefinition]}`.
  3. If subprocess execution or JSON-RPC handshake fails or times out after 10 seconds, the endpoint returns `{"status": "error", "error": str, "latency_ms": float}` with status code `200` (diagnostic payload).

### [REQ-MCP-009] Settings Studio Key-Value Environment Editor & Live Handshake Preview UI
- **Type**: Ubiquitous
- **Description**: The Settings Studio UI SHALL provide an interactive dynamic key-value row editor for environment variables and a "Test Connection & Discover" button that displays discovered tool badges.
- **Acceptance Criteria**:
  1. The MCP Server form includes an "Environment Variables" section with `Add Variable` button, dynamic key/value row deletion, and masked password-type inputs for values.
  2. Clicking "Test Handshake & Discover" triggers `POST /api/settings/mcp/test`, displays a loading spinner, and renders a summary panel showing latency and green pill badges for each discovered tool name and its description.
  3. Form submission (`Save & Mount`) sends all configured key-value pairs in the payload.

### [REQ-MCP-010] Agent Forge Dynamic MCP Pack Binding & Granular Tool RBAC Assignment
- **Type**: Event-Driven
- **Description**: When an agent profile is edited in Agent Forge Studio, the UI and backend SHALL dynamically expose all currently mounted MCP servers as selectable skill packs under "Skill Scopes & Tool Permissions".
- **Acceptance Criteria**:
  1. The `GET /api/agents/skills` or `GET /api/settings/mcp` metadata is used by Agent Forge to render an "External MCP Tool Packs" group in the Skill Scopes card.
  2. Toggling an MCP server pack checkbox automatically adds or removes all tools belonging to that MCP server (`mcp_<server>_*`) in the agent profile's `allowed_tool_names`.
  3. Saving the agent profile persists the updated tool names to SQLite via `store.save_agent_override()`.
