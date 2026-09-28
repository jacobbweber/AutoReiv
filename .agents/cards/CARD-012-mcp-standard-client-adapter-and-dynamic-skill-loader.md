# [CARD-012] MCP Standard Client Adapter and Dynamic Skill Loader

> **Status**: Done
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/mcp-client-and-dynamic-tools/
> **Labels**: `type:feature`

---

## 1. Why / Intent
Enable seamless integration with Model Context Protocol (MCP) servers via stdio JSON-RPC 2.0 and provide 3-Tier Tool Resolution Pipeline with BM25 ranking and dynamic skill manual loading.

---

## 2. What to Build
MCPClientAdapter, MCPClientManager, ToolRanker, DynamicSkillLoader, mcp_servers settings persistence, and ScopedToolRegistry dynamic MCP mounting.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] [REQ-MCP-001]: Standard JSON-RPC 2.0 Stdio Transport.
- [x] [REQ-MCP-002]: MCP Tools Discovery (tools/list) & Scoped Tool Mounting.
- [x] [REQ-MCP-003]: Resilient MCP Tool Execution (tools/call) & Output Formatting.
- [x] [REQ-MCP-004]: 3-Tier Tool Resolution & Fast In-Memory BM25 Tool Ranker.
- [x] [REQ-MCP-005]: MCP Server Settings Persistence & REST Management API.
- [x] [REQ-MCP-006]: Portable Markdown Skill Manual Discovery.
- [x] Automated tests green via `pytest` (309/309 passed).
- [x] Zero lint errors via `ruff check .` & `eslint`.
- [x] Pre-flight verification passed 100%.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
