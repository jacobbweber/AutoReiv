# [CARD-377] MCP Lifecycle Handshake and Standard Client Compliance

> **Status**: Completed
> **Created**: 2026-09-19
> **Spec Reference**: `docs/specs/mcp-lifecycle-handshake/requirements.md`
> **Labels**: `type:feature`, `domain:mcp`, `domain:kernel`, `domain:ui`

---

## 1. Why / Intent
Support standard Model Context Protocol servers (like the official Blender Lab FastMCP server and open MCP tools) by implementing the mandatory MCP lifecycle handshake (`initialize` followed by `notifications/initialized`). Enable flexible, seamless connection flows across both stdio and remote HTTP/SSE transports in Settings Studio and Forge Studio.
Furthermore, ensure MCP servers connect cleanly into AutoReiv's Demand-Paged Capability Engine so that agents (including the default `autoreiv` orchestrator) dynamically discover MCP servers in their system prompt index, demand-page MCP tools via intent and `activate_skill`, and support intuitive bulk selection in Agent Forge.

---

## 2. What to Build
- **Phase 1 (Transport & Handshake - Completed)**:
  - **`src/infrastructure/mcp/client_adapter.py`**: Implement automatic `initialize` and `notifications/initialized` handshake in `MCPClientAdapter` for both stdio and remote transports with graceful legacy fallback.
  - **`src/web/routers/settings.py`**: Update `save_mcp_server` and `test_mcp_server_connection` to accept and pass `transport`, `url`, and `headers` to `mcp_manager` and `MCPClientAdapter`.
  - **`src/web/templates/index.html` & `src/web/static/modules/studios/settings.js`**: Add Transport dropdown and Remote URL input to Global Settings Studio's Add MCP Server form.
- **Phase 2 (Demand Paging, Autoreiv Scoping & Forge UX)**:
  - **`src/application/kernel/agent_kernel.py`**: Make the system message capability index dynamic so it reflects registered MCP server domains (e.g. `blender`) alongside platform skills. Add MCP server intent matching in `_match_intent_skills()`. Enhance `_resolve_active_tools()` priority sorting to support `mcp_{skill}_` tools.
  - **`src/application/skills/platform_primitives.py`**: Enhance `activate_skill()` to recognize MCP tool families (e.g. `activate_skill(["blender"])` mounts `mcp_blender_*` tools).
  - **`src/application/kernel/tool_registry.py`**: Support MCP tool scoping for `autoreiv` when MCP skills are active or servers are configured.
  - **`src/web/templates/index.html`**: Add missing `<button id="selectAllToolsBtn">` and `<button id="clearAllToolsBtn">` above `forgeToolsGrid` in Agent Forge.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-MCP-HANDSHAKE-001]`: `MCPClientAdapter` executes `initialize` and `notifications/initialized` before subsequent requests.
- [x] `[REQ-MCP-HANDSHAKE-002]`: `MCPClientAdapter` falls back gracefully if an older/simple server does not support `initialize`.
- [x] `[REQ-MCP-HANDSHAKE-003]`: Global Settings Studio allows configuring both `stdio` and `sse` transports and mounts them via `mcp_manager`.
- [x] `[REQ-MCP-HANDSHAKE-004]`: System message capability index dynamically lists active/registered MCP server domains in addition to baseline platform skills.
- [x] `[REQ-MCP-HANDSHAKE-005]`: `AgentKernel._match_intent_skills()` and `activate_skill()` recognize MCP server domains and dynamically mount `mcp_<server>_*` tools.
- [x] `[REQ-MCP-HANDSHAKE-006]`: `ScopedToolRegistry` allows active MCP tools to execute cleanly for `autoreiv` and specialist agents without silent dropping.
- [x] `[REQ-MCP-HANDSHAKE-007]`: Agent Forge provides functioning "Select All" and "Clear All" buttons above `forgeToolsGrid`.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .` and `npm run test:unit:frontend`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/card-377-mcp-lifecycle-handshake` branch cut from `qa`.
