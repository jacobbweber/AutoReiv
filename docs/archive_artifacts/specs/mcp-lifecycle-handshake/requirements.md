# Requirements Specification: MCP Lifecycle Handshake & Standard Client Compliance

> **Spec Status**: Approved
> **Target Release**: v1.1.0
> **Primary Component**: MCP Infrastructure (`src/infrastructure/mcp`)

---

## 1. Executive Summary & Intent
Enable seamless, standard-compliant connectivity to modern Model Context Protocol (MCP) servers (including the official Blender Lab FastMCP server and open MCP tools). Implements the mandatory MCP protocol lifecycle handshake (`initialize` and `notifications/initialized`) before discovering or executing tools, and harmonizes transport options across Settings and Forge.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-MCP-HANDSHAKE-001]: Standard MCP Initialization Handshake
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL execute the official Model Context Protocol initialization handshake ('initialize' followed by 'notifications/initialized') before sending any subsequent JSON-RPC request to an MCP server.`
- **Acceptance Criteria**:
  - [ ] Given a newly spawned stdio MCP server process, when `_send_jsonrpc` or `list_tools` is called, the client adapter performs the `initialize` exchange with `protocolVersion`, `capabilities`, and `clientInfo`.
  - [ ] After receiving a successful initialization response, the client adapter transmits the `notifications/initialized` notification without waiting for a reply.
  - [ ] Subsequent requests (`tools/list`, `tools/call`, `ping`) proceed within the initialized session without repeating initialization.

### [REQ-MCP-HANDSHAKE-002]: Legacy Server Initialization Tolerance & Fallback
- **Type**: Complex
- **EARS Statement**: `WHEN an MCP server returns an error or unsupported response to 'initialize', THE SYSTEM SHALL log a warning and proceed gracefully to attempt direct tool discovery.`
- **Acceptance Criteria**:
  - [ ] Given a simple or legacy server that does not recognize `initialize`, the client adapter catches the error and marks initialization attempted so subsequent calls are not permanently blocked.

### [REQ-MCP-HANDSHAKE-003]: Global Settings Remote MCP Transport Support
- **Type**: Event-Driven
- **EARS Statement**: `WHEN configuring an MCP server in Global Settings Studio, THE SYSTEM SHALL support selecting between 'stdio' and 'sse' transports and specifying a remote URL.`
- **Acceptance Criteria**:
  - [ ] The Global Settings MCP server schema and endpoints accept `transport`, `url`, and `headers` alongside `command` and `env`.
  - [ ] Backend router `save_mcp_server` passes `transport`, `url`, and `headers` to `mcp_manager.mount_server`.
  - [ ] Backend router `test_mcp_server_connection` passes `transport`, `url`, and `headers` to `MCPClientAdapter`.

---

## 3. Non-Functional & Boundary Constraints
- **Performance**: Handshake overhead < 50ms over stdio.
- **Security**: Passed environment variables and auth headers are isolated per server.
- **Reliability**: Subprocess termination cleanly cleans up child processes and open sockets.

---

## 4. Out of Scope
- Direct raw TCP socket protocol negotiation inside AutoReiv (the Blender add-on architecture requires the `blender-mcp` Python bridge for stdio translation).
- Modifying third-party Blender extensions.
