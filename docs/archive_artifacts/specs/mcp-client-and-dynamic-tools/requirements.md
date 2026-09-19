# Requirements Specification: MCP Standard Client Adapter & 3-Tier Dynamic Tool Resolution

> **Spec Status**: Approved  
> **Target Release**: Milestone 15 (`CARD-012`)  
> **Primary Component**: AutoReiv.MCP, AutoReiv.Kernel, AutoReiv.Web  

---

## 1. Executive Summary & Intent
Enable seamless integration with external Model Context Protocol (MCP) servers via stdio JSON-RPC 2.0 transport, runtime tool discovery, and dynamic skill manual loading. Introduce a sub-millisecond 3-Tier Tool Resolution Pipeline in `AgentKernel` that preserves LLM context budgets by ranking and mounting only relevant tool definitions per turn.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-MCP-001]: MCP Stdio Subprocess Transport & JSON-RPC 2.0 Lifecycle
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an MCP server configuration is mounted, THE SYSTEM SHALL spawn the specified subprocess using stdio communication, handle stdout/stderr asynchronously, and perform JSON-RPC 2.0 requests with proper process cleanup on shutdown.`
- **Acceptance Criteria**:
  - [ ] Given a valid executable and arguments, when `_send_jsonrpc` is called, then the request is formatted with `"jsonrpc": "2.0"` and responses are parsed from stdio.
  - [ ] Given an unreachable or failing command, when initialization occurs, then a structured error is returned without hanging the asyncio event loop.

### [REQ-MCP-002]: Remote Tool Discovery & Namespace Scoping
- **Type**: Event-Driven
- **EARS Statement**: `WHEN querying an active MCP server, THE SYSTEM SHALL invoke the 'tools/list' method, namespace each returned tool as 'mcp_<server_name>_<tool_name>', and register its JSON Schema into ScopedToolRegistry.`
- **Acceptance Criteria**:
  - [ ] Given an MCP server returning 3 tools, when `list_tools()` runs, then all 3 are returned with prefixed names, descriptions, and input schemas.
  - [ ] Given duplicate tool names across different MCP servers, when registered, then the namespace prefix guarantees collision-free registration.

### [REQ-MCP-003]: Resilient Tool Invocation & Output Formatting
- **Type**: Event-Driven
- **EARS Statement**: `WHEN an agent triggers an MCP tool call, THE SYSTEM SHALL dispatch 'tools/call' with arguments to the subprocess, enforce a 30-second timeout, and return a ToolResult with parsed text/json output.`
- **Acceptance Criteria**:
  - [ ] Given a valid tool execution, when the subprocess returns content blocks, then text content is merged and returned as success.
  - [ ] Given a subprocess timeout or error payload, when executed, then a `ToolResult(success=False, error=...)` is cleanly returned.

### [REQ-MCP-004]: 3-Tier Dynamic Tool Resolution & BM25 Tool Ranker
- **Type**: State-Driven
- **EARS Statement**: `WHILE an agent has more authorized tools than max_active_tools (default: 6), THE SYSTEM SHALL retain pinned core tools and rank the remaining authorized tools using fast local BM25 scoring against the user query, mounting only top-ranked tools into the completion payload.`
- **Acceptance Criteria**:
  - [ ] Given an agent with 40 authorized tools and `max_active_tools=6`, when a user asks to inspect CPU metrics, then sysadmin/CPU tools are ranked top and passed to the LLM.
  - [ ] Given pinned core tools (`delegate_task`), when ranking occurs, then pinned tools are always retained in the active tool definitions.
  - [ ] The ranking calculation must execute in under 2 milliseconds without burning LLM tokens.

### [REQ-MCP-005]: MCP Server Settings Persistence & REST Management API
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL expose REST endpoints 'GET /api/settings/mcp', 'POST /api/settings/mcp', and 'DELETE /api/settings/mcp/{name}' and persist server configurations in SQLite state storage.`
- **Acceptance Criteria**:
  - [ ] Given a new MCP server configuration (name, command, env), when posted, then it is persisted in SQLite and tested for connectivity.
  - [ ] Given an existing MCP server, when deleted, then its tools are unmounted from `ScopedToolRegistry`.

### [REQ-MCP-006]: Portable Markdown Skill Manual Discovery
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL discover and parse 'SKILL.md' manuals containing YAML frontmatter and JSON tool blocks into executable skill definitions.`
- **Acceptance Criteria**:
  - [ ] Given a directory with `SKILL.md` files, when `scan_skills_directory` runs, then all valid manuals are parsed and returned with name, description, instructions, and tools.

---

## 3. Non-Functional & Boundary Constraints
- **Performance**: Tool ranking must complete in $< 2\text{ ms}$.
- **Security**: MCP tool executions run under subprocess environment isolation; sensitive API keys are not logged.
- **Reliability**: Subprocess failures or timeouts do not crash the web server or Agent Kernel.

---

## 4. Out of Scope
- Dynamic SSE / remote HTTP MCP transport (stdio subprocess is primary for Milestone 15).
- Auto-installing third-party npm / pip packages on behalf of the user.

