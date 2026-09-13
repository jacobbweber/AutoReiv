# [CARD-052] MCP Server Environment Variables Live Discovery and Agent Forge Pack Binding

> **Status**: Done
> **Created**: 2026-08-27
> **Spec Reference**: docs/specs/mcp-env-discovery-and-agent-forge/
> **Labels**: `type:feature`, `milestone:16`

---

## 1. Why / Intent
Enable production-grade MCP integration by supporting per-server environment variables (API keys, auth tokens, DB URLs), live handshake testing and tool discovery preview in Settings Studio, and granular MCP pack assignment per agent in Agent Forge Studio.

---

## 2. What to Build
1. **MCP Server Environment Variables**:
   - Key-Value editor in Settings Studio MCP server modal.
   - Environment variables passed to stdio subprocess in `MCPClientAdapter` with sensitive credential masking in the UI.
2. **Live Test Handshake & Tool Discovery (`/api/settings/mcp/test`)**:
   - Backend probe endpoint that executes a test stdio handshake and `tools/list` without requiring saving first.
   - Live discovery preview rendering tool name pills and descriptions in Settings Studio.
3. **Agent Forge Studio MCP Pack Binding**:
   - Dynamically list mounted MCP servers as selectable skill packs under "Skill Scopes & Tool Permissions" in Agent Forge.
   - Seamlessly grant/revoke all tools of an MCP server to/from the selected agent profile.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `[REQ-MCP-007]`: Per-server Environment Variables persistence in SQLite and process injection in `MCPClientAdapter`.
- [x] `[REQ-MCP-008]`: Probe endpoint `POST /api/settings/mcp/test` executing stdio handshake and returning discovered tools with latency diagnostics.
- [x] `[REQ-MCP-009]`: Settings Studio Key-Value Environment Editor & Live Handshake Preview UI.
- [x] `[REQ-MCP-010]`: Agent Forge Studio dynamic MCP Pack binding & per-agent tool permission updates.
- [x] Unit and contract tests green via `pytest` (313/313) and `vitest` (50/50).
- [x] Multi-studio Playwright smoke tests green (4/4).
- [x] Zero lint errors via `ruff` and `eslint`.

---

## 4. Constraints & Honor Flags
- Strict isolated `feat/mcp-env-discovery-and-agent-forge` branch cut from `qa`.
- Zero breaking changes to existing passing tests.
- Context budget safety: all MCP tools continue to route through the 3-Tier Tool Resolution Pipeline and `ToolRanker`.

