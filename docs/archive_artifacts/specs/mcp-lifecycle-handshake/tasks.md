# Implementation Tasks: MCP Lifecycle Handshake & Standard Client Compliance

> **Spec Reference**: `docs/specs/mcp-lifecycle-handshake/requirements.md`  
> **Target Branch**: `feat/card-377-mcp-lifecycle-handshake`  
> **TDD Invariant**: Red -> Green -> Refactor for every slice.

---

## Task Matrix

### Slice 1: MCPClientAdapter Handshake Implementation (TDD)
- [x] **1.1 (Red)**: Write unit tests in `tests/unit/test_mcp_client_handshake.py` verifying that `MCPClientAdapter` sends `initialize` and `notifications/initialized` before `tools/list` `[REQ-MCP-HANDSHAKE-001]`.
- [x] **1.2 (Red)**: Write test verifying graceful fallback if server errors on `initialize` `[REQ-MCP-HANDSHAKE-002]`.
- [x] **1.3 (Green)**: Implement `_ensure_initialized` in `MCPClientAdapter` for stdio and remote transports.
- [x] **1.4 (Refactor)**: Verify all existing MCP tests pass without regression.

### Slice 2: Global Settings Router & Mount Harmony
- [x] **2.1 (Red)**: Add integration tests in `tests/integration/test_settings_mcp_endpoints.py` verifying `save_mcp_server` and `test_mcp_server_connection` handle `transport`, `url`, and `headers` `[REQ-MCP-HANDSHAKE-003]`.
- [x] **2.2 (Green)**: Update `save_mcp_server` and `test_mcp_server_connection` in `src/web/routers/settings.py`.
- [x] **2.3 (Green)**: Update Global Settings HTML form and `settings.js` to expose Transport and Remote URL fields.

### Slice 3: Verification & Definition of Done
- [x] **3.1**: Verify live with `scratch/blender_mcp/mcp` and `scratch/test_blender_mcp.py` to confirm 26 tools discover smoothly.
- [x] **3.2**: Run full preflight verification suite (`python .agents/skills/rtm-sync/scripts/preflight.py` or pytest + ruff).
- [x] **3.3**: Update `CHANGELOG.md` under `## [Unreleased]`.
