---
id: CARD-627
title: "Tools Studio re-splits a saved MCP command on spaces, so Test, Enable/Disable and Connect break any argument that contains a space"
type: bug
status: Ready
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-627-mcp-command-round-trip]
  checks: []
branch: feat/card-627-mcp-command-round-trip
log: {minutes: 0, qa_runs: 0, findings: 0}
created: 2026-10-03
related:
  - CARD-516
  - CARD-424
  - CARD-421
---

# CARD-627 Tools Studio re-splits a saved MCP command on spaces, so Test, Enable/Disable and Connect break any argument that contains a space

## Problem
In the CARD-516 live check (2026-10-03, :8770), a platform MCP server saved through the API with the command `["python.exe", "-c", "import nonexistent_card516_mod"]` was tested from its Tools Studio row (Test). The probe ran `python.exe -c import nonexistent_card516_mod` and reported `SyntaxError: invalid syntax` instead of the real `ModuleNotFoundError` (screenshot `autoreiv-qa\ui1003k\03-desktop-tools-studio-test-failed.png`).

The same round trip runs when the row's Disable/Enable or Connect is clicked: those re-save the server, so the stored command is overwritten with the split one. Any argument with a space breaks: `python -c "<code>"`, a script under `C:\Program Files\...` or `C:\Users\<name with space>\...`, `--arg "two words"`.

## Cause
`serverToSaveBody` in `tools_studio_catalog.js` joins `server.command` with spaces and passes it to `buildMcpSaveBody`, which splits `commandText` on whitespace (`commandText.split(/\s+/)`). `tools_studio.js` uses it for toggle (L482), connect (L520) and test-saved (L533). The add/edit form has the same single-text-box split.

## Change
- Re-save and Test a stored server with its stored `command` array unchanged; only the form builds a command from text.
- In the form, split like a shell (quotes keep spaces; Windows backslashes stay literal) and show the stored command with quotes where needed so Edit, Save round-trips. Vitest for both; smoke: a saved server with a spaced argument survives Disable, Enable and Test.

## What dies
Saved MCP commands that a click on Enable or Test silently rewrites.

## Proof
- Journey `card-627-mcp-command-round-trip`: save `python -c "import sys; print(1)"`-style and `C:\Program Files\...` commands; Disable, Enable, Test and Edit, Save keep the stored array byte-identical (desktop and phone).

## Plan and decisions

## Findings
- (from the CARD-516/522 live check, 2026-10-03; docs/findings.md)

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|

## Release note
MCP server commands with spaces in an argument (quoted code, paths under Program Files) keep working after Test, Enable or Disable in Tools Studio.
