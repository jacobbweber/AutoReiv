---
name: Enterprise MCP Server Engineering & Deployment
description: Scaffold FastMCP servers, run JSON-RPC protocol tests, deploy Docker containers with health checks, and register MCP endpoints into AutoReiv.
version: 1.0.0
tier: platform
requires_tools:
  - scaffold_mcp_server
  - test_mcp_server
  - deploy_mcp_container
  - register_mcp_service
safety:
  read_only: false
  requires_hitl: true
  untrusted_input_allowed: false
verification:
  kind: assertion
  rule: Authored MCP server passes AST and schema tests, container enforces healthcheck, and AutoReiv successfully mounts endpoint.
---

# Enterprise MCP Server Engineering & Deployment

End-to-end engineering, testing, containerization, and registration of custom Model Context Protocol (MCP) servers for internal enterprise APIs, databases, hardware, and external services.

## Operating Principles

1. **Strict Type Safety & Schemas**:
   - Every MCP tool function must expose typed parameter annotations and structured docstrings.
   - Pydantic models and JSON-RPC 2.0 schema invariants must be verified before deployment.

2. **Single Lever Invariant**:
   - Automated registration through `register_mcp_service` uses the exact same canonical store (`store.set_setting("mcp_servers", ...)`) and mounting pipeline as Tools Studio platform attach (`POST /api/settings/mcp`).
   - Never create parallel or shadow registration endpoints.

3. **Mandatory Container Healthchecks**:
   - Production Docker deployments must define an active `HEALTHCHECK` instruction to prevent silent zombie processes.
   - Deployments lacking health monitoring must be rejected.

4. **Graceful Subprocess Fallback**:
   - If the Docker daemon or CLI is unavailable, smoothly fall back to local `stdio` subprocess execution so developer agents can continue without interruption.

## Available Tools

- `scaffold_mcp_server`: Scaffolds a complete FastMCP project structure (`server.py`, `pyproject.toml`, `Dockerfile`, `README.md`).
- `test_mcp_server`: Performs AST syntax verification, JSON-RPC schema validation, and tool contract testing.
- `deploy_mcp_container`: Builds and runs a containerized server with health checking, with graceful fallback to `stdio`.
- `register_mcp_service`: Registers the server in AutoReiv's canonical store, mounts it live via `MCPClientManager`, and writes the companion `SKILL.md`.

## Operating Protocol

### 1. Interface Discovery & Design
- Clarify tool names, inputs, outputs, and descriptions with the operator.
- Formulate schemas as clean JSON objects with parameter types, descriptions, and required constraints.

### 2. Project Scaffolding
- Call `scaffold_mcp_server` specifying `name`, `description`, and `tools_spec`.
- FastMCP project is generated under `scratch/mcp_servers/<name>` (or specified destination directory).

### 3. Protocol & Schema Testing
- Call `test_mcp_server` pointing to the project directory.
- Verify AST syntax validity and JSON-RPC tool schemas.
- Inspect any diagnostic warnings or errors before proceeding to deployment.

### 4. Containerization & Deployment
- Call `deploy_mcp_container` with the project path, target port, and environment variables.
- If Docker is running, the image is built and container launched with healthcheck validation.
- If Docker is absent, the tool automatically selects local stdio transport.

### 5. AutoReiv Canonical Registration
- Call `register_mcp_service` with the server name, transport (`stdio` or `sse`), and endpoint or command.
- Verify that AutoReiv reports `mounted: True` with discovered tool count.
- Companion runbook is automatically created under `$DATA_DIR/skills/mcp-<name>/SKILL.md`.

## Pitfalls

- **Missing HEALTHCHECK**: Container deployment will be rejected if the Dockerfile does not specify a `HEALTHCHECK`.
- **Invalid Tool Identifiers**: Tool names must use alphanumeric characters and underscores only. Spaces and special characters violate JSON-RPC standards.
- **Overlapping Ports**: Ensure target port (e.g. 8000, 8080) does not conflict with existing local services.

## Done-when

- FastMCP server project is scaffolded and passing all `test_mcp_server` contract checks.
- Container is deployed with valid health checking or configured for local stdio transport.
- Server is registered in AutoReiv's canonical store and active in `MCPClientManager`.
- Discovered tools appear in AutoReiv with generated companion `SKILL.md` runbook.
