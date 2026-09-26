---
id: CARD-516
title: "An MCP server that cannot start is reported as \"ok\" and \"mounted\" (0 tools) by Settings Test and Save"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-511
  - CARD-424
  - CARD-394
labels:
  - type:bug
  - area:mcp
  - area:settings
  - P3
---

# [CARD-516] An MCP server that cannot start is reported as "ok" and "mounted"

> **Status**: Ready (found in the CARD-511 scratch reproduction, 2026-09-26 ~1:20 AM ET, qa `6f066514`). Not next: it misleads the operator but damages no data and does not block CARD-511, which reads `last_error` itself. The queue is CARD-511, CARD-497, CARD-512, CARD-498, then Education Studio.
> **Related**: CARD-511 (checks Developer's `register_mcp_service`; decision D9 leaves the Settings routes alone), CARD-424 (MCP save mounts and unmounts), CARD-394 (MCP engineering tools)
> **Labels**: `type:bug`, `area:mcp`, `area:settings`, `P3`

## Problem

On a scratch server (port 8767, fresh data `scratch\c511_rb`):
- `POST /api/settings/mcp/test` with a stdio command that cannot start (a script importing the `mcp` SDK, which is not installed) returned **`status: ok`, 0 tools**.
- `POST /api/settings/mcp` with `python -c "import nonexistent_c511_mod"` returned **`status: saved, mounted: true, tools_count: 0`**, and `GET /api/settings/mcp` shows `is_mounted: true`. This survives a restart.

Cause: `MCPClientAdapter.list_tools` (`client_adapter.py` L232-242) catches every error, stores it in `last_error` and returns `[]`. The Test route and `reconcile_saved_mcp_server` treat `[]` as success. The same thing happens when Developer's `scaffold_mcp_server` output (which imports `mcp.server.fastmcp`) is registered with the default command in the AutoReiv venv, where the SDK is not installed.

## Change

Test and Save report `status: error` / `mounted: false` with `last_error` when `list_tools` failed, and keep the config saved (operator-owned) with a visible error badge in Settings. Optionally, say in the scaffold output that the server needs `pip install mcp` in its own environment.

## Done when

A server that cannot start shows an error in Settings Test and Save, with the reason; a working server is unchanged; tests cover both.
