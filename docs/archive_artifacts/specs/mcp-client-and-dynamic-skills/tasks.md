# Implementation Tasks: MCP Standard Client Adapter & Dynamic Skill Loader

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks must reference their corresponding `[REQ-MCP-xxx]` tags.

---

## Vertical Slice Breakdown

### Slice 1: MCP JSON-RPC Stdio Client Adapter
- [x] **Task 1.1** `[REQ-MCP-001]`, `[REQ-MCP-002]`, `[REQ-MCP-003]`: [RED] Write unit tests in `tests/unit/mcp/test_mcp_client_adapter.py` verifying JSON-RPC 2.0 framing, `tools/list` schema transformation, and `tools/call` invocation.
- [x] **Task 1.2** `[REQ-MCP-001]`, `[REQ-MCP-002]`, `[REQ-MCP-003]`: [GREEN] Implement `MCPClientAdapter` in `src/infrastructure/mcp/client_adapter.py`.

### Slice 2: Dynamic Skill Manual Loader & ScopedToolRegistry MCP Mounting
- [x] **Task 2.1** `[REQ-MCP-004]`, `[REQ-MCP-005]`: [RED] Write unit tests in `tests/unit/skills/test_dynamic_skill_loader.py` verifying `SKILL.md` markdown parsing and dynamic registration into `ScopedToolRegistry`.
- [x] **Task 2.2** `[REQ-MCP-004]`, `[REQ-MCP-005]`: [GREEN] Implement `DynamicSkillLoader` in `src/application/skills/dynamic_loader.py` and add MCP tool mount helper in `ScopedToolRegistry`.

### Slice 3: MCP Settings Persistence & REST Endpoints
- [x] **Task 3.1** `[REQ-MCP-006]`: [RED] Write integration tests in `tests/unit/web/test_mcp_web_api.py` verifying `GET /api/mcp/servers` and `POST /api/mcp/servers`.
- [x] **Task 3.2** `[REQ-MCP-006]`: [GREEN] Implement MCP server settings persistence and REST routes in `src/web/app.py`.

### Slice 4: Verification, Traceability, & PR Gate
- [x] **Task 4.1**: Run complete test suite and linters (`pytest`, `ruff check .`).
- [x] **Task 4.2**: Synchronize `docs/rtm.json` and run `python .agents/skills/rtm-sync/scripts/verify_rtm.py --pre-flight`.
- [x] **Task 4.3**: Conclude Milestone 12 and merge into `qa`.
