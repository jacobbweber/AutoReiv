# Implementation Tasks: MCP Standard Client Adapter & 3-Tier Dynamic Tool Resolution

> **Linked Spec**: [`requirements.md`](./requirements.md) | [`design.md`](./design.md)  
> **Traceability Key**: All tasks reference corresponding `[REQ-MCP-xxx]` tags.  

---

## Vertical Slice Breakdown

### Slice 1: Fast In-Memory BM25 Tool Ranker & 3-Tier Resolution in Kernel
- [ ] **Task 1.1** `[REQ-MCP-004]`: [RED] Write failing unit tests in `tests/unit/kernel/test_tool_ranker.py` asserting keyword relevance ranking, pinned tool retention, and sub-millisecond execution.
- [ ] **Task 1.2** `[REQ-MCP-004]`: [GREEN] Implement `ToolRanker` in `src/application/kernel/tool_ranker.py` using BM25 scoring over tool names, descriptions, and parameter keys.
- [ ] **Task 1.3** `[REQ-MCP-004]`: [GREEN] Integrate `ToolRanker` into `AgentKernel.run_turn` and `AgentKernel.stream_turn` in `src/application/kernel/agent_kernel.py` when total authorized tools exceed `max_active_tools`.
- [ ] **Task 1.4** `[REQ-MCP-004]`: [REFACTOR] Clean up ranking edge cases (empty queries, special characters, tie-breaking).

### Slice 2: MCP Stdio Subprocess Transport, Tool Discovery, and Execution
- [ ] **Task 2.1** `[REQ-MCP-001, REQ-MCP-002, REQ-MCP-003]`: [RED] Write failing unit tests in `tests/unit/mcp/test_mcp_client_adapter.py` verifying JSON-RPC 2.0 requests, `tools/list` namespace prefixing (`mcp_<server>_<tool>`), tool execution via `tools/call`, and timeout resilience.
- [ ] **Task 2.2** `[REQ-MCP-001, REQ-MCP-002, REQ-MCP-003]`: [GREEN] Refine `MCPClientAdapter` in `src/infrastructure/mcp/client_adapter.py` with robust async stdio management, timeout handling, and structured output extraction.
- [ ] **Task 2.3** `[REQ-MCP-002]`: [GREEN] Ensure `ScopedToolRegistry.mount_mcp_tool` cleanly integrates MCP tools with per-agent RBAC enforcement.

### Slice 3: MCP Settings Persistence & REST Management Endpoints
- [ ] **Task 3.1** `[REQ-MCP-005]`: [RED] Write failing contract tests in `tests/unit/web/test_mcp_web_api.py` for `GET /api/settings/mcp`, `POST /api/settings/mcp`, and `DELETE /api/settings/mcp/{name}`.
- [ ] **Task 3.2** `[REQ-MCP-005]`: [GREEN] Implement SQLite persistence methods `get_mcp_servers`, `save_mcp_server`, `delete_mcp_server` in `src/infrastructure/memory/repositories/settings.py`.
- [ ] **Task 3.3** `[REQ-MCP-005]`: [GREEN] Implement REST router endpoints in `src/web/routers/settings.py` and auto-mounting lifecycle in `src/web/app.py`.

### Slice 4: Dynamic Markdown Skill Manual Loader
- [ ] **Task 4.1** `[REQ-MCP-006]`: [RED] Write failing unit tests in `tests/unit/skills/test_dynamic_skill_loader.py` for `SKILL.md` frontmatter and embedded JSON schema discovery.
- [ ] **Task 4.2** `[REQ-MCP-006]`: [GREEN] Refine `DynamicSkillLoader` in `src/application/skills/dynamic_loader.py`.

### Slice 5: Quality Gate & Pre-Flight Verification
- [ ] **Task 5.1**: Run full preflight suite (`pytest`, `ruff`, `eslint`, `vitest`, `playwright`).
- [ ] **Task 5.2**: Update `docs/rtm.json` mapping `[REQ-MCP-001]` - `[REQ-MCP-006]` and run `verify_rtm.py`.
- [ ] **Task 5.3**: Update `CHANGELOG.md` under `[Unreleased]`.

