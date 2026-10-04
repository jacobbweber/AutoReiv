---
id: CARD-516
title: "An MCP server that cannot start is reported as \"ok\" and \"mounted\" (0 tools) by Settings Test and Save"
status: In Review
created: 2026-09-26
branch: feat/card-516-522-mcp-start-errors-and-gap-prefill
related:
  - CARD-511
  - CARD-424
  - CARD-394
labels:
  - type:bug
  - area:mcp
  - area:settings
  - P3
needs_decision: none
milestone: M25
---

# [CARD-516] An MCP server that cannot start is reported as "ok" and "mounted"

> **Status**: In Review (2026-10-03, branch `feat/card-516-522-mcp-start-errors-and-gap-prefill`, not merged). Found in the CARD-511 scratch reproduction, 2026-09-26.
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

## Built (2026-10-03, branch `feat/card-516-522-mcp-start-errors-and-gap-prefill`)
- `MCPClientManager.mount_server` raises `MCPMountError` with the start error when `list_tools()` swallowed one (`adapter_start_error`), closes the process, mounts nothing and remembers the reason (`get_mount_errors()`). A good mount or an unmount clears it. A server that starts and lists no tools still mounts with 0 tools.
- Save (platform and agent) keeps the config and returns `status: saved`, `mounted: false`, `error` and a new `last_error` (the reason alone). `GET /api/settings/mcp` and `GET /api/agents/{id}/mcp` carry `last_error` for a server that failed, including a failed auto-mount at startup.
- Test (`/api/settings/mcp/test`, `/api/agents/{id}/mcp/test`) returns `status: error` with the reason instead of `ok, 0 tools`.
- Settings and Tools Studio rows show a red **Failed to start** badge with a one-line reason (a Python traceback keeps its header and last line; the full text is the tooltip). The Settings line counts "N failed to start"; the save toast says "Saved X, but it did not start: <reason>". app.js v2.0.107.
- Developer's `scaffold_mcp_server` diagnostics now say the server needs the MCP SDK (`pip install mcp`) or the Docker image; the AutoReiv environment does not have it.
- Decision: Save keeps `status: "saved"` (the config is saved) and reports the failure through `mounted: false` plus `last_error`, rather than `status: "error"`. The Tools Studio toast and the CARD-424 tests key on that shape.
- Tests: `tests/integration/test_card516_mcp_start_errors.py` (7, real subprocesses: a command that dies on import, the raw fixture server in good and empty modes; manager, platform Test/Save/list, disable clears the error, startup auto-mount failure, agent Test/Save/list), Vitest `card_516_mcp_start_error_badge.test.js` (5), smoke TC-52 desktop and phone.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| Test `python -c "import nonexistent_card516_mod"` (API) | API | pass | `status: error`, reason ends `ModuleNotFoundError: No module named 'nonexistent_card516_mod'`; the raw fixture server: `ok`, 2 tools |
| Save the broken server, then the working one, then list (API) | API | pass | broken: saved, `mounted: false`, `last_error`; working: mounted, 2 tools; list: broken `is_mounted: false` + reason, working `is_mounted: true`, `last_error: null`; agent Test of the broken one: `error` |
| Settings > Connections | desktop | pass | "2 platform MCP servers attached (1 mounted, 1 failed to start)."; c516-broken: Failed to start + one-line reason; c516-weather: Mounted (2) |
| Tools Studio > MCP attach | desktop | pass | c516-broken: Failed to start + reason; c516-weather: Mounted (2 tools). The row's Test showed a SyntaxError because Tools Studio re-splits the stored command (CARD-627) |
| Settings > Connections | phone | pass | same badge and reason, wrapped |

Live on :8770 (sandbox of `fb89c37a`, then `15645c26`), nemotron-3.5-lightning (Spark), 2026-10-03 11:05-11:10 PM ET. No console errors.

Screenshots (`C:\Users\jacob\AppData\Local\Temp\autoreiv-qa\ui1003k\`): `01-desktop-settings-mcp-failed-to-start.png`, `02-desktop-tools-studio-mcp-rows.png`, `03-desktop-tools-studio-test-failed.png`, `10-phone-settings-mcp-failed-to-start.png`.

## Findings
- (from this build and live check, 2026-10-03; docs/findings.md) Tools Studio re-splits a saved MCP command on spaces on Test, Enable/Disable and Connect: CARD-627.

## Release note
An MCP server that cannot start now shows "Failed to start" with the reason in Settings and Tools Studio, instead of "ok" or "mounted (0 tools)".
