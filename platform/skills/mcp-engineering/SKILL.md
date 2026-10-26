---
name: Enterprise MCP Server Engineering & Deployment
description: Scaffold FastMCP servers, run JSON-RPC protocol tests, deploy Docker containers with health checks, and register MCP endpoints into AutoReiv.
tools:
- scaffold_mcp_server
- test_mcp_server
- deploy_mcp_container
- register_mcp_service
version: 1.0.0
tier: platform
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

## Dual packaging lanes [CARD-423]

MCP is one lane, not the only lane.

- **Platform / built-in tools** already run inside AutoReiv. They do not need an MCP server.
- **Native custom tools** use the `native-tool-engineering` skill and `register_native_tool`. No MCP server. Sandbox plus ToolPolicyGate / HITL still apply.
- **MCP-backed custom tools** are this skill. After `register_mcp_service` (or Capabilities Studio attach on `/api/settings/mcp` or `/api/agents/{id}/mcp`), the tools show in Capabilities Studio grouped under **that server's name**.
- MCP **hosting** stays in Settings. Do not move it into Capabilities Studio.
- A filesystem path in developer chat ("here is a folder of scripts, one tool per entry") is conversation context. Call `plan_native_folder` or walk the directory yourself. There is no Capabilities Studio folder picker. Choose native or MCP per the operator's packaging note, then build that lane. The note is not already applied.

## Operating Principles

1. **Strict Type Safety & Schemas**:
   - Every MCP tool function must expose typed parameter annotations and structured docstrings.
   - Pydantic models and JSON-RPC 2.0 schema invariants must be verified before deployment.

2. **Single Lever Invariant**:
   - Automated registration through `register_mcp_service` uses the exact same canonical store (`store.set_setting("mcp_servers", ...)`) and mounting pipeline as Capabilities Studio platform attach (`POST /api/settings/mcp`).
   - Never create parallel or shadow registration endpoints.

3. **Mandatory Container Healthchecks**:
   - Production Docker deployments must define an active `HEALTHCHECK` instruction to prevent silent zombie processes.
   - Deployments lacking health monitoring must be rejected.

4. **Graceful Subprocess Fallback**:
   - If the Docker daemon or CLI is unavailable, smoothly fall back to local `stdio` subprocess execution so developer agents can continue without interruption.

## Available Tools

- `scaffold_mcp_server`: Scaffolds a complete FastMCP project structure (`server.py`, `pyproject.toml`, `Dockerfile`, `README.md`) under `$AUTOREIV_PROJECTS_DIR/<name>` (or the selected project) with optional custom Python tool bodies (`code` in `tools_spec`).
- `test_mcp_server`: Performs AST syntax verification, JSON-RPC schema validation, and tool contract testing.
- `deploy_mcp_container`: Builds and runs a containerized server on the host Docker daemon (with `HEALTHCHECK`, optional host `volumes` bind-mounts, and `http://host.docker.internal:<port>/sse` endpoint resolution when running inside Docker), with graceful fallback to `stdio`.
- `register_mcp_service`: Registers the server in AutoReiv's canonical store, mounts it live via `MCPClientManager`, writes the companion `SKILL.md`, and activates `mcp-<name>` in the current session so the mounted `mcp_<name>_*` tools are immediately callable.

## Operating Protocol

### 1. Interface Discovery & Design
- Clarify tool names, inputs, outputs, and descriptions with the operator.
- Formulate schemas as clean JSON objects with parameter types, descriptions, required constraints, and optional `code` (the Python function body string for each tool).

### 2. Project Scaffolding
- Call `scaffold_mcp_server` specifying `name`, `description`, and `tools_spec` (including `"code"` for custom tool implementations, e.g. listing a host directory).
- FastMCP project is generated under `$AUTOREIV_PROJECTS_DIR/<name>` (shared with the host at `$AUTOREIV_PROJECTS_HOST_PATH` when running in Docker) or the specified `target_dir`.

### 3. Protocol & Schema Testing
- Call `test_mcp_server` pointing to the project directory (`project_path` from `scaffold_mcp_server`).
- Verify AST syntax validity and JSON-RPC tool schemas.
- Inspect any diagnostic warnings or errors before proceeding to deployment.

### 4. Containerization & Deployment (Docker & Host Bind-Mounts)
- Call `deploy_mcp_container` with `project_path`, `port` (default `8765`; never `8000` which AutoReiv uses), optional `env_vars`, and optional `volumes` (e.g. `["/home/spark:/host:ro"]` when the MCP server needs read-only access to a host directory).
- If Docker is running (including via `/var/run/docker.sock` from inside `autoreiv-control-plane`), the image is built and the sibling container is launched on the host Docker daemon with `MCP_TRANSPORT=sse` and healthcheck validation.
- `deploy_mcp_container` returns `url: "http://host.docker.internal:<port>/sse"` when AutoReiv is inside Docker (or `http://localhost:<port>/sse` on the host).
- If Docker is absent, the tool automatically selects local `stdio` transport and returns `command`.

### 5. AutoReiv Canonical Registration & Immediate Use
- Call `register_mcp_service` with `name`, `transport` (`"sse"` when `deploy_mcp_container` returned `mode: "docker"`, or `"stdio"` when it returned `mode: "stdio"`), and `url_or_command` (pass the `url` or `command` returned by `deploy_mcp_container`).
- Verify that AutoReiv reports `mounted: True` with discovered tool names (`mcp_<name>_<tool>`).
- Companion runbook is automatically created under `$DATA_DIR/skills/mcp-<name>/SKILL.md` and activated in the current session so you can call `mcp_<name>_<tool>` on the very next step.
- **Registration checks the server first [CARD-511].** AutoReiv starts it, `tools/list` must return at least one tool with a valid name and an object `inputSchema`, then it calls one tool once (`sample_tool`, default the first) with `sample_arguments` or the minimum built from its schema. For a server that needs secrets, the network, or has side effects, pass `sample_call: "skip"` with a `skip_reason`.
- If the result starts **`Not registered:`**, nothing was saved or mounted. Tell the operator the error, fix the server, and call `register_mcp_service` again.

## Pitfalls

- **Missing HEALTHCHECK**: Container deployment will be rejected if the Dockerfile does not specify a `HEALTHCHECK`.
- **Invalid Tool Identifiers**: Tool names must use alphanumeric characters and underscores only. Spaces and special characters violate JSON-RPC standards.
- **Overlapping Ports**: Use port `8765` (or another free port above `8700`); never use `8000` (AutoReiv's own port).

## Done-when

- FastMCP server project is scaffolded and passing all `test_mcp_server` contract checks.
- Container is deployed with valid health checking or configured for local stdio transport.
- Server is registered in AutoReiv's canonical store and active in `MCPClientManager`.
- Discovered `mcp_<name>_*` tools are mounted and verified in the current session.

