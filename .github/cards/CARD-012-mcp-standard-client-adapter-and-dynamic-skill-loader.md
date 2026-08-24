# [CARD-012] MCP Standard Client Adapter and Dynamic Skill Loader

> **Status**: Ready
> **Created**: 2026-08-23
> **Spec Reference**: docs/specs/mcp-client-and-dynamic-skills/
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Enable integration with Model Context Protocol (MCP) servers via stdio JSON-RPC and support runtime dynamic skill manual loading

---

## 2. What to Build
MCPClientAdapter, DynamicSkillLoader, mcp_servers settings persistence, and ScopedToolRegistry MCP mounting

---

## 3. Acceptance Criteria (Definition of Done)
- [ ] Requirement 1: ...
- [ ] Requirement 2: ...
- [ ] Automated tests green via `pytest`.
- [ ] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa`.
