---
id: CARD-517
title: "An MCP tool call that crashes the server is reported as success with empty output"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-511
labels:
  - type:bug
  - area:mcp
  - P2
---

# [CARD-517] An MCP tool call that crashes the server is reported as success

> **Status**: Ready (found in the CARD-511 scratch reproduction, 2026-09-26 ~1:20 AM ET, qa `6f066514`). **Recommended, folded into CARD-511 (its decision D10)**, because CARD-511's MCP pass rule depends on a truthful call result, and because an agent is told a failed action succeeded. Closes with CARD-511 if D10 is accepted.
> **Related**: CARD-511 (REQ-511-013)
> **Labels**: `type:bug`, `area:mcp`, `P2`

## Problem

A minimal stdio MCP server (`scratch\c511_mcp\server_raw.py`) that lists one tool and raises (and exits) on `tools/call`: `MCPClientAdapter.call_tool` returned **`{"success": true, "output": {}}`** under both the Proactor and Selector event loops (`scratch\c511_mcp_probe2.py`).

Cause: `_sync_exchange` (`client_adapter.py` L162-176) returns `""` when `readline()` hits EOF before the process has been reaped (`poll()` is still `None`). `_send_jsonrpc` (L215-221) then returns `{}` for an empty line, and `call_tool` treats `{}` as success.

## Change

An empty line, or a process that has exited, is an error: raise with the exit code and stderr, so `call_tool` returns `success: false`. Test first with the raw fixture server.

## Done when

Calling a tool that crashes its server returns `success: false` with the server's error; normal calls are unchanged.
