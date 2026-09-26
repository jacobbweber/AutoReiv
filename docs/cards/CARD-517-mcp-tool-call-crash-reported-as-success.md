---
id: CARD-517
title: "An MCP tool call that crashes the server is reported as success with empty output"
status: Done
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

> **Status**: Done (folded into CARD-511 as decision D10 / REQ-511-013, accepted 2026-09-26 ~1:52 AM ET). Fixed in `fd53cf83` on `feat/card-511-tool-check`: `_sync_exchange` and `_send_jsonrpc` raise with the exit code and stderr instead of returning an empty result, so `call_tool` returns `success: false`. Tests: `test_card517_*` in `tests/unit/mcp/test_mcp_client_adapter.py`. Ships with the CARD-511 merge. Found in the CARD-511 scratch reproduction, 2026-09-26 ~1:20 AM ET, qa `6f066514`.
> **Related**: CARD-511 (REQ-511-013)
> **Labels**: `type:bug`, `area:mcp`, `P2`

## Problem

A minimal stdio MCP server (`scratch\c511_mcp\server_raw.py`) that lists one tool and raises (and exits) on `tools/call`: `MCPClientAdapter.call_tool` returned **`{"success": true, "output": {}}`** under both the Proactor and Selector event loops (`scratch\c511_mcp_probe2.py`).

Cause: `_sync_exchange` (`client_adapter.py` L162-176) returns `""` when `readline()` hits EOF before the process has been reaped (`poll()` is still `None`). `_send_jsonrpc` (L215-221) then returns `{}` for an empty line, and `call_tool` treats `{}` as success.

## Change

An empty line, or a process that has exited, is an error: raise with the exit code and stderr, so `call_tool` returns `success: false`. Test first with the raw fixture server.

## Done when

Calling a tool that crashes its server returns `success: false` with the server's error; normal calls are unchanged.
