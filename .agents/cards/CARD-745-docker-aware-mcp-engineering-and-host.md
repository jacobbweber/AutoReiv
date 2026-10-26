---
id: CARD-745
title: "Make MCP engineering Docker-aware and support host/Docker MCP container deployment from inside Docker"
type: feature
status: Done
priority: P2
milestone: M34
needs_decision: none
proof:
  journeys: [card-745-docker-aware-mcp-engineering-and-host]
  checks: [tests/integration/test_card745_docker_aware_mcp_engineering.py]
branch: feat/card-745-docker-aware-mcp-engineering-and-host
log: {minutes: 35, qa_runs: 2, findings: 1}
created: 2026-10-24
---

# CARD-745 Make MCP engineering Docker-aware and support host/Docker MCP container deployment from inside Docker

## Intent
When `AutoReiv` runs inside Docker (`autoreiv-control-plane`), it needs to be able to scaffold, test, containerize, and deploy new MCP servers (including host-access MCP servers that bind-mount host directories) onto the host Docker daemon, and then register and call those MCP servers over `http://host.docker.internal:<port>/sse`.

## Goal
From inside the running `autoreiv-control-plane` Docker container, `AutoReiv` can scaffold a new FastMCP server under `/data/projects/<name>` (shared with the host at `AUTOREIV_PROJECTS_HOST_PATH`), deploy it as a sibling Docker container (with optional host bind-mounts like `/home/spark:/host:ro`), register it at `http://host.docker.internal:<port>/sse`, and call its tools (such as listing directories on the host) live in Chat.

## Change
- `Dockerfile`, `docker-compose.yml`: include the static `docker` CLI binary in the runtime image, pass `AUTOREIV_PROJECTS_HOST_PATH` into the container environment, and mount `/var/run/docker.sock` so `deploy_mcp_container` can build and launch sibling MCP containers on the host daemon.
- `src/application/skills/mcp_docker_helpers.py`, `src/application/skills/mcp_engineering_tools.py`:
  1. Default `scaffold_mcp_server` `target_dir` to `$AUTOREIV_PROJECTS_DIR/<name>` (falling back to `$AUTOREIV_DATA_DIR/projects/<name>`) instead of `scratch/mcp_servers/<name>`, and generate dual-mode `stdio` + HTTP/SSE JSON-RPC 2.0 `server.py` (`MCP_TRANSPORT=sse`, `/health` and `/sse` routes, and custom tool implementation bodies via `code` in `tools_spec`).
  2. In `deploy_mcp_container`, translate container paths under `$AUTOREIV_PROJECTS_DIR` to `$AUTOREIV_PROJECTS_HOST_PATH` when needed, support optional `volumes: list[str]` (e.g. `["/home/spark:/host:ro"]`), replace any stale container with the same name (`docker rm -f`), wait for `/health`, and return `http://host.docker.internal:<port>/sse` when `AUTOREIV_DEPLOY_MODE=docker` (or inside `/.dockerenv`).
  3. In `register_mcp_service`, normalize `localhost` / `127.0.0.1` URLs to `host.docker.internal` when running inside Docker and `localhost` is unreachable, and record `mcp-<name>` session skill activation (`record_session_skill_activation` + `session_activated_skills_from_history`) so the newly mounted `mcp_<Name>_*` tools are immediately callable in the same turn and subsequent turns.
- `platform/skills/mcp-engineering/SKILL.md`: document the Docker/Host MCP workflow (scaffolding into `/data/projects/<name>`, passing custom tool `code` and host `volumes`, deploying to the host Docker daemon, and registering via `http://host.docker.internal:<port>/sse`).

## What dies
- Hardcoded `scratch/mcp_servers` default target directory in `scaffold_mcp_server` (replaced by `$AUTOREIV_PROJECTS_DIR/<name>`).
- Hardcoded `http://localhost:{port}/sse` return URL in `deploy_mcp_container` when running inside Docker.

## Proof
- Journey `card-745-docker-aware-mcp-engineering-and-host`:
  1. Opens `AutoReiv` in Chat, activates `mcp-engineering`, scaffolds a host-directory MCP server (`host_fs_mcp`) with a `list_host_dir` tool, tests it with `test_mcp_server`, deploys it with `deploy_mcp_container`, registers it with `register_mcp_service`, and calls `mcp_host_fs_mcp_list_host_dir` to list a real directory.
- Checks: `tests/integration/test_card745_docker_aware_mcp_engineering.py`.

## Plan and decisions
- Approved by Jacob (`Option A`): Make `scaffold_mcp_server`, `deploy_mcp_container`, and `register_mcp_service` Docker- and host-aware (`$AUTOREIV_PROJECTS_DIR`, host volume mounts, `host.docker.internal` endpoint resolution, and auto-activating the `mcp-<name>` companion skill for immediate session use).

## Findings
- Fixed (in-area): `session_activated_skills_from_history` in `src/application/skills/session_skills.py` only restored skills activated via `skill_view`, so `mcp-<name>` companion skills registered via `register_mcp_service` were not kept active across follow-up turns in the same session. Updated `register_mcp_service` to include `companion_skill_id` and `session_activated_skills_from_history` to restore `mcp-<name>` from `register_mcp_service` tool results.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-745-docker-aware-mcp-engineering-and-host` | desktop | PASS | `/tmp/autoreiv-qa/card-745/card-745-docker-aware-mcp-engineering-and-host-desktop-01-in-chat-autoreiv-opens-mcp-engineering-scaffolds.png`, `/tmp/autoreiv-qa/card-745/card-745-docker-aware-mcp-engineering-and-host-desktop-02-in-chat-autoreiv-deploys-host-fs-mcp-in-docker-w.png`, `/tmp/autoreiv-qa/card-745/card-745-docker-aware-mcp-engineering-and-host-desktop-03-verify-host-fs-mcp-is-registered-in-canonical-mc.png` |
| `card-745-docker-aware-mcp-engineering-and-host` | phone | PASS | `/tmp/autoreiv-qa/card-745/card-745-docker-aware-mcp-engineering-and-host-phone-02-in-chat-autoreiv-deploys-host-fs-mcp-in-docker-w.png`, `/tmp/autoreiv-qa/card-745/card-745-docker-aware-mcp-engineering-and-host-phone-03-verify-host-fs-mcp-is-registered-in-canonical-mc.png` |

## Release note
- **Added**: Made `mcp-engineering` Docker- and host-aware (`$AUTOREIV_PROJECTS_DIR` scaffolding, custom tool implementation bodies, host volume mounts, `host.docker.internal` endpoint resolution, and immediate session mounting of `mcp-<name>` companion skills) (`CARD-745`).

