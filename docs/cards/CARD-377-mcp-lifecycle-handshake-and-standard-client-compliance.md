# [CARD-377] MCP Lifecycle Handshake and Standard Client Compliance

> **Status**: In Review
> **Created**: 2026-09-19
> **Spec Reference**: `docs/specs/mcp-lifecycle-handshake/requirements.md`
> **Labels**: `type:feature`, `domain:mcp`

---

## 1. Why / Intent
Support standard Model Context Protocol servers (like the official Blender Lab FastMCP server and open MCP tools) by implementing the mandatory MCP lifecycle handshake (`initialize` followed by `notifications/initialized`). Enable flexible, seamless connection flows across both stdio and remote HTTP/SSE transports in Settings Studio and Forge Studio.

---

## 2. What to Build
- **`src/infrastructure/mcp/client_adapter.py`**: Implement automatic `initialize` and `notifications/initialized` handshake in `MCPClientAdapter` for both stdio and remote transports with graceful legacy fallback.
- **`src/web/routers/settings.py`**: Update `save_mcp_server` and `test_mcp_server_connection` to accept and pass `transport`, `url`, and `headers` to `mcp_manager` and `MCPClientAdapter`.
- **`src/web/templates/index.html` & `src/web/static/modules/studios/settings.js`**: Add Transport dropdown and Remote URL input to Global Settings Studio's Add MCP Server form.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-MCP-HANDSHAKE-001]`: `MCPClientAdapter` executes `initialize` and `notifications/initialized` before subsequent requests.
- [x] `[REQ-MCP-HANDSHAKE-002]`: `MCPClientAdapter` falls back gracefully if an older/simple server does not support `initialize`.
- [x] `[REQ-MCP-HANDSHAKE-003]`: Global Settings Studio allows configuring both `stdio` and `sse` transports and mounts them via `mcp_manager`.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/card-377-mcp-lifecycle-handshake` branch cut from `qa`.
