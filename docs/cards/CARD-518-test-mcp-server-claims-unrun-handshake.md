---
id: CARD-518
title: "Developer's test_mcp_server claims a JSON-RPC handshake it never runs"
status: Ready
created: 2026-09-26
branch: qa
related:
  - CARD-511
  - CARD-394
labels:
  - type:bug
  - area:mcp
  - area:agents
  - P3
---

# [CARD-518] Developer's `test_mcp_server` claims a handshake it never runs

> **Status**: Ready (found while refining CARD-511, 2026-09-26 ~1:20 AM ET, qa `6f066514`). Not next: after CARD-511, registration itself runs the server once, so a broken server can no longer go live through `register_mcp_service`. This only makes Developer's pre-check misleading. The queue is CARD-511, CARD-497, CARD-512, CARD-498, then Education Studio.
> **Related**: CARD-511 (real MCP check in `tool_check.py`), CARD-394 (origin)
> **Labels**: `type:bug`, `area:mcp`, `area:agents`, `P3`

## Problem

`MCPEngineeringTools.test_mcp_server` (`mcp_engineering_tools.py` L277-424) only parses `server.py` with the AST and finds decorated functions. It never starts the server, yet it returns `jsonrpc_tested: true` and "Simulated JSON-RPC handshake verified initialize and tools/list". It also ignores `test_args`, so it calls nothing. Developer can therefore tell the operator that a server was tested when it cannot even import (as with the `mcp` SDK missing from the AutoReiv venv).

## Change

Make `test_mcp_server` call CARD-511's MCP check without saving anything (start, list, optional sample call with `test_tool`/`test_args`), or rename the result to say it is a static check only, and drop `jsonrpc_tested`.

## Done when

`test_mcp_server` either really starts the server or clearly says it did not; tests cover a server that cannot start.
