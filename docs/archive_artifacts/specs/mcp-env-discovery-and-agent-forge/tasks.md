# Task Matrix: MCP Environment Variables, Live Tool Discovery, and Agent Forge Pack Binding

## Vertical Slices

### Slice 1: Subprocess Environment Injection & Persistence (`[REQ-MCP-007]`)
- [ ] Task 1.1: [RED] Write unit test in `tests/unit/mcp/test_mcp_client_adapter.py` asserting environment variable merging and subprocess injection.
- [ ] Task 1.2: [GREEN] Update `MCPClientAdapter._send_jsonrpc` to merge `os.environ` with `self.env`.
- [ ] Task 1.3: [REFACTOR] Ensure safe masking and validation.

### Slice 2: Live Handshake & Tool Discovery Endpoint (`[REQ-MCP-008]`)
- [ ] Task 2.1: [RED] Write integration test in `tests/unit/web/test_mcp_web_api.py` for `POST /api/settings/mcp/test`.
- [ ] Task 2.2: [GREEN] Implement probe handler in `src/web/routers/settings.py` measuring latency, listing tools, and cleaning up subprocess.
- [ ] Task 2.3: [REFACTOR] Add structured timeout and error payload formatting.

### Slice 3: Settings Studio Dynamic Key-Value Editor & Live Discovery Preview (`[REQ-MCP-009]`)
- [ ] Task 3.1: [RED] Add DOM elements and assertions in `tests/e2e/smoke.spec.js` for environment variables editor and test connection button.
- [ ] Task 3.2: [GREEN] Implement dynamic key-value rows and test connection flow in `src/web/static/modules/studios/settings.js` and `src/web/templates/index.html`.
- [ ] Task 3.3: [REFACTOR] Style tool discovery pill badges and secret masks.

### Slice 4: Agent Forge MCP Pack Binding (`[REQ-MCP-010]`)
- [ ] Task 4.1: [RED] Write frontend unit test in `tests/unit/frontend/agents.test.js` or e2e test verifying MCP pack checkboxes grant/revoke `mcp_<server>_*` tools.
- [ ] Task 4.2: [GREEN] Update `src/web/static/modules/studios/agents.js` to fetch mounted MCP servers and render external MCP packs in the Skill Scopes card.
- [ ] Task 4.3: [REFACTOR] Ensure tool name synchronization when saving agent profile.

### Slice 5: Unified Pre-Flight & DoD Gate
- [ ] Task 5.1: Execute `python .agents/skills/rtm-sync/scripts/preflight.py`.
- [ ] Task 5.2: Update `docs/rtm.json` and `CHANGELOG.md`.
