# [CARD-184] Remote MCP Server Pack Scaffolding and Docker Execution

> **Status**: Done
> **Created**: 2026-09-07
> **Spec Reference**: `docs/specs/mcp-remote-scaffolding.md`
> **Labels**: `type:feature`, `factory`, `mcp`, `docker`

---

## 1. Why / Intent
AutoReiv previously treated Model Context Protocol (MCP) servers as local companion scripts sharing internal Python modules (`src.infrastructure.mcp.pack_server`), and generated loose ad-hoc tools under `tools/` even when MCP deliverable architecture was requested. 

In real deployments, MCP servers must be treated as independent, external network services running in Docker or on dedicated remote hosts (e.g., Hyper-V hypervisors, cloud VMs, edge devices). When MCP architecture is selected, the Agent Training Factory must generate a completely self-contained, zero-dependency MCP server package (`mcp/`) containing dual-mode stdio/HTTP server execution, Dockerfile, docker-compose, daemon scripts, and documentation, with **zero loose files in `tools/`**.

---

## 2. What to Build
1. **Self-Contained Dual-Mode MCP Server Package (`AuthorPhase`)**:
   - `mcp/server.py`: Zero internal AutoReiv dependencies. Built-in `PackMCPServer` handling JSON-RPC 2.0 over both stdio (for local battery testing) and HTTP/SSE (`--mode http --port <PORT>`).
   - `mcp/Dockerfile`: Minimal container definition exposing port 8080.
   - `mcp/docker-compose.yml`: Compose service definition.
   - `mcp/requirements.txt`: Lightweight dependencies.
   - `mcp/run.ps1` & `mcp/run.sh`: Host daemon execution scripts.
   - `mcp/README.md`: Complete remote deployment and connection instructions.
   - Purge `tools/` from `files_map` when `deliverable_type == "mcp"`.
2. **Phase Alignments**:
   - `ScenarioVerifyPhase`: Scan `mcp/server.py` in tool code corpus.
   - `VerifyPhase`: Run `run_mcp_battery` on `mcp/server.py` without synthesizing fallback `tools/*.py`.
   - `OptimizePhase`: Handle MCP server deliverables cleanly.
3. **Pack Promotion (`agent_training_factory.py`)**:
   - Save `mcp/` and `skills/` into pack, strictly omitting `tools/`.
   - Persist remote `mcp_servers` configuration in `pack.json` (`transport="sse"`, `url="http://localhost:8080/sse"`).
4. **Kernel Tool RBAC & Lifecycle**:
   - `ScopedToolRegistry.get_tools_for_agent()` and `_execute_inner()` authorize tools from agent `mcp_servers`.
   - `lifespan` in `src/web/app.py` auto-mounts enabled per-agent MCP servers at startup.
   - `POST /api/agents/{agent_id}/mcp/{server_name}/mount` endpoint and UI Connect button.

---

## 3. Acceptance Criteria (Definition of Done)
- [x] `AuthorPhase` scaffolds all 7 MCP package files under `mcp/` and zero files under `tools/` when `deliverable_type == 'mcp'`.
- [x] Scaffolded `mcp/server.py` is 100% self-contained (zero imports of `src.infrastructure.*`), and runs in both stdio and HTTP modes.
- [x] `VerificationBatteryService.run_mcp_battery()` verifies the scaffolded MCP server cleanly across all 4 stages.
- [x] Pack promotion writes `mcp/` and `skills/` with zero `tools/` directory created.
- [x] End-to-end Hyper-V training creates a clean `hyperv` pack with remote MCP server.
- [x] Docker build and run of the generated Hyper-V MCP server succeeds and responds to remote HTTP JSON-RPC probes.
- [x] Automated tests green via `pytest`.
- [x] Zero lint errors via `ruff check .`.

---

## 4. Constraints & Honor Flags
- Standard honor constraints apply.
- Local `qa` branch is source of truth.
- When deliverable is MCP, strictly no loose tools under `tools/`.
- MCP servers must be treated as external network services communicating over HTTP/SSE.
