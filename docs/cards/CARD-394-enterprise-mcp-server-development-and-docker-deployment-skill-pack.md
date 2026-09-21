---
id: CARD-394
title: "Enterprise MCP Server Development and Docker Deployment Skill Pack"
status: Done
created: 2026-09-20
adr: 0054
labels:
  - type:feature
  - domain:mcp
  - domain:skills
  - area:infrastructure
  - area:devops
---

# [CARD-394] Enterprise MCP Server Development and Docker Deployment Skill Pack

> **Status**: Done  
> **Created**: 2026-09-20  
> **ADR Reference**: [ADR-0054](file:///d:/Projects/Active/AutoReiv/docs/adr/0054-autonomic-os-state-machine-demand-paging-and-mechanical-governance.md)  
> **Labels**: `type:feature`, `domain:mcp`, `domain:skills`, `area:infrastructure`, `area:devops`  

---

## 1. Why / Intent (Beat 1)

Operators need a seamless way to expand AutoReiv's capabilities by creating new, custom Model Context Protocol (MCP) servers for internal enterprise services, custom databases, third-party APIs (e.g. Jira, Redis, Snowflake), or specialized hardware.

This card delivers the **`mcp-engineering` Platform Skill Pack**. It equips AutoReiv agents (such as Developer and Sysadmin) with end-to-end capabilities to:
1. Socratic requirement gathering for new custom tools and input/output schemas.
2. Scaffolding enterprise-grade MCP server projects (Python FastMCP or TypeScript MCP SDK) with strict Pydantic/Zod schemas.
3. Authoring automated unit tests that verify JSON-RPC 2.0 `tools/list` and `tools/call` contracts.
4. Packaging into production-ready Docker containers with non-root security standards.
5. Deploying the container locally via Docker and automatically registering the new server into AutoReiv's MCP client configuration so agents can immediately use it.

---

## 2. What AutoReiv Does Now (Beat 2)

1. AutoReiv can consume external MCP servers configured in Settings Studio (`MCPClientManager`), but provides no built-in tools or runbooks for developing new MCP servers.
2. Creating a new MCP server requires manual external coding, manually writing Dockerfiles, running terminal commands, and manually configuring endpoints in Settings.
3. No automated validation exists to verify that a newly authored MCP server complies with protocol standards before deployment.

---

## 3. What Will Change (Beat 3)

1. **`mcp-engineering` Skill Pack (`src/infrastructure/skills/seeds/mcp-engineering/`)**:
   - Canonical `SKILL.md` runbook with Matt Pocock operational blueprint (`## Operating Principles`, `## Available Tools`, `## Done-When`).
   - Guides the agent through standard phases: Interface Design $\rightarrow$ Code Generation $\rightarrow$ Protocol Verification $\rightarrow$ Docker Containerization $\rightarrow$ AutoReiv Registration.
2. **MCP Engineering Tools**:
   - `scaffold_mcp_server(name, description, tools_spec, target_dir)`: Generates canonical FastMCP project with `server.py`, `pyproject.toml`, `Dockerfile`, and `README.md`.
   - `test_mcp_server(project_path)`: Executes simulated JSON-RPC requests against the server script to verify `initialize`, `tools/list`, and `tools/call` without requiring an active external client.
   - `deploy_mcp_container(project_path, container_name, port, env_vars)`: Builds the Docker image and starts the container via Docker CLI / API with health monitoring (graceful stdio fallback if Docker is absent).
   - `register_mcp_service(name, transport, url_or_command, headers, env)`: Adds the server into AutoReiv's canonical MCP store (`store.set_setting("mcp_servers")`) and mounts it via `MCPClientManager`, triggering dynamic capability discovery and companion `SKILL.md` authoring.
3. **Single Lever Invariant for MCP Mounting**:
   - Preserves the manual **Add MCP Server** button and modal in Settings Studio (`#view-settings`) as the primary human lever for mounting pre-existing external servers (GitHub, SQLite, Blender, etc.).
   - Agent tool `register_mcp_service` writes to the exact same store configuration and invokes the exact same `mcp_manager.mount_server` pipeline, guaranteeing zero duplicate data paths.
4. **Agent Integration**:
   - Mounts `mcp-engineering` onto `platform-packs/developer` and makes it available in Agent Forge for custom engineering agents.

---

## 4. What Dies Today (The Prune List - Beat 4)

- Retire manual, error-prone authoring of boilerplate MCP server scripts and Dockerfiles.
- Eliminate disconnected, non-standardized Docker deployments for custom agent tools.
- Never maintain divergent registration pipelines: manual Settings Studio and agent automated mounting share the exact same `store.set_setting("mcp_servers")` and `mcp_manager.mount_server` execution path.

---

## 5. Acceptance Criteria (EARS Syntax)

- **[REQ-394-001] (Ubiquitous)**: THE SYSTEM SHALL provide the `mcp-engineering` platform skill pack adhering to ADR-0054 capability contracts.
- **[REQ-394-002] (Event-Driven)**: WHEN an operator requests a new MCP server, THE AGENT SHALL scaffold a valid MCP project structure with typed schemas and automated protocol tests.
- **[REQ-394-003] (State-Driven)**: WHILE testing an authored server, THE `test_mcp_server` TOOL SHALL execute simulated JSON-RPC `tools/list` and `tools/call` handshakes and verify zero contract errors.
- **[REQ-394-004] (Event-Driven)**: WHEN containerization is requested, THE `deploy_mcp_container` TOOL SHALL build the Docker image, run the container with health check validation, and register the endpoint with AutoReiv.
- **[REQ-394-005] (Negative Assertion)**: Automated tests shall explicitly assert that container deployments without health check endpoints or with invalid JSON-RPC schemas are rejected with remediation diagnostics.

---

## 6. Constraints & Verification Plan

- Feature branch: `feat/CARD-394-mcp-engineering-skill` cut from `qa`.
- Unit tests: `tests/unit/skills/test_mcp_engineering_tools.py`, `tests/unit/mcp/test_mcp_scaffolding.py`.
- Integration tests: `tests/integration/mcp/test_mcp_dev_deploy_lifecycle.py`.
- Linting: `ruff check .` and `npm run lint:frontend` with 0 errors.
- Preflight: `python .agents/skills/preflight/scripts/preflight.py`.
