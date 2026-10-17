---
id: CARD-703
title: "Local inference port auto-probing in Models Studio and startup"
type: feature
status: In Review
priority: P3
milestone: M30
needs_decision: none
proof:
  journeys: [card-703-local-inference-port-auto-probing]
  checks: [tests/unit/models/test_card703_local_port_probe.py, tests/unit/frontend/card_703_local_model_probe.test.js]
branch: feat/card-703-local-inference-port-auto-probing
log: {minutes: 15, qa_runs: 2, findings: 0}
created: 2026-10-17
---

# CARD-703 Local inference port auto-probing in Models Studio and startup

## Intent
Adapted from `Agent-OS` (`agent_os/local_setup.py`, `docs/architecture-comparison-crucible-agent-os.md` §6 & §7.2): operators running vLLM or Ollama locally on standard ports (`8000`, `8006`, `11434`, or `AUTOREIV_PROBE_PORTS`) should be able to discover served `/v1/models` endpoints with one click in Models Studio (and on first-run startup when no working provider is configured) without manually typing base URLs and model IDs.

## Goal
Add a deterministic local port probe (`POST /api/models/probe-local`) that scans configured local ports (`8000, 8006, 11434` by default), parses OpenAI-compatible `/v1/models` lists, and surfaces discovered local servers as one-click "Use model" cards in Models Studio.

## Change
- Implement local model server probing (`probe_local_endpoints` and `activate_discovered_model` in `src/application/models/local_probe.py`) with a 1.0 s timeout across `AUTOREIV_PROBE_PORTS` (default `8000, 8006, 11434` and configured local/LAN provider hosts), filtering out non-model HTTP servers.
- Expose `POST /api/models/probe-local` in `src/web/routers/settings.py` and mount a **Local Inference Auto-Probe** card (`#settingsLocalProbeCard` / `#scanLocalServersBtn`) in Settings Studio (`src/web/static/modules/studios/settings_local_model_probe.js`) that lists discovered models and lets the operator activate one in a single click.

## What dies
- Nothing.

## Proof
- Journey `card-703-local-inference-port-auto-probing`:
  1. Open Settings Studio (`#view-settings`), trigger local server probing (`#scanLocalServersBtn`), verify the active local inference servers (`127.0.0.1:8006` vLLM and `192.168.1.29:11434` Ollama) and 5 models are discovered and rendered as selectable cards while port `8000` web server is excluded, and verify clicking **Use Model** activates and persists the selected provider and model on desktop and phone.
- Checks:
  - `tests/unit/models/test_card703_local_port_probe.py`
  - `tests/unit/frontend/card_703_local_model_probe.test.js`

## Plan and decisions
- Approved by Jacob under `CARD-698` Option 2 (2026-10-17).

## Findings
- None.

## Results
| Journey | Viewport | Result | Notes |
|---|---|---|---|
| `card-703-local-inference-port-auto-probing` | desktop | PASS | 3/3 steps pass; discovered 5 models across 2 servers (`127.0.0.1:8006` vLLM & `192.168.1.29:11434` Ollama), excluded port `8000`, one-click `Use Model` activated and persisted `qwen3.8:latest` |
| `card-703-local-inference-port-auto-probing` | phone | PASS | 3/3 steps pass; discovered 5 models across 2 servers, one-click activation persisted, 0px horizontal overflow |

Screenshots:
- `/tmp/autoreiv-qa/card-703/card-703-local-inference-port-auto-probing-desktop-02-click-scan-local-servers-and-verify-discovered-m.png`
- `/tmp/autoreiv-qa/card-703/card-703-local-inference-port-auto-probing-desktop-03-click-use-model-on-a-discovered-card-and-verify-.png`
- `/tmp/autoreiv-qa/card-703/card-703-local-inference-port-auto-probing-phone-03-click-use-model-on-a-discovered-card-and-verify-.png`

## Release note
- Added local inference port auto-probing (`8000, 8006, 11434`) in Models Studio and `/api/models/probe-local` [CARD-703].
