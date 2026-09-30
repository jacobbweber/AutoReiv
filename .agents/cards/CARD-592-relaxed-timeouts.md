---
id: CARD-592
title: "All AutoReiv timeouts relaxed for local models; main waits in Settings > Reply limits"
status: Done
completed: 2026-09-30
created: 2026-09-30
branch: card/592-relaxed-timeouts
related:
  - CARD-567
  - CARD-585
  - CARD-588
  - CARD-258
labels:
  - type:improvement
  - area:gateway
  - area:web
  - P2
needs_decision: none
milestone: M24
---

# [CARD-592] All AutoReiv timeouts relaxed for local models; main waits in Settings > Reply limits

> **Status**: Done (merged into qa 2026-09-30)
> **Labels**: `type:improvement`, `area:gateway`, `area:web`, `P2`

## Why

Jacob (2026-09-30): local models fill the KV cache, think for a long time and queue behind other chats, so every
AutoReiv timeout should be very relaxed. Short timeouts stay only on pure health / connectivity probes.

## Change

- Settings > Reply limits (setting `reply_limits`, resolution setting > env > default) now holds:
  - `max_seconds` per reply (from first token): 1200 -> **7200** (env `AUTOREIV_MAX_REPLY_SECONDS`)
  - `provider_idle_seconds` (provider silence, before the first byte and between chunks): 900 -> **1800**
    (env `AUTOREIV_PROVIDER_IDLE_SECONDS`, legacy `GATEWAY_DEFAULT_TIMEOUT_SECONDS` still read)
  - `phase_seconds` (job phase / developer turn / routine call): 300 -> **21600** (env `STANDING_PHASE_LLM_TIMEOUT_SECONDS`)
  - `helper_seconds` (gap analysis 4 s, distillation 4.5 s, Skill Studio 60 s): -> **1800** (env `AUTOREIV_HELPER_CALL_SECONDS`)
- Provider adapters (OpenAI/vLLM, Ollama, Anthropic): the read timeout is resolved per request (saved setting applies
  without a restart); connect 15/30 -> 60 s, write 15/30 -> 600 s, pool 15/30 -> 600 s. Model-list probes use 15 s.
- Chat SSE stream: `: keepalive` comment every 15 s while nothing else is sent (clients skip non-`data:` lines).
- Job budgets: max phases 16 -> 256, max hand-offs 4 -> 64 (recorded, not enforced today).
- Tool defaults: sandbox / shell / SSH exec / MCP tool call 30 -> 600 s (MCP tools/list stays 30 s; SSH connect 15 s);
  project checks cap 3600 -> 14400 s; git worktree 30 -> 300 s; docker build 180 -> 1800 s, docker run 30 -> 120 s;
  wiki fetch 12 -> 60 s.
- Frontend: `waitUntilIdle` (resume after the tab's stream ends) 15 min -> 6 h; Education mint abort 45 s -> 30 min.
  Approval and send requests have no client timeout (browser fetch has none).
- `.env.example` no longer sets `GATEWAY_DEFAULT_TIMEOUT_SECONDS=180`.

## Kept short (probes)

Connectivity tests (settings/agents 10 s, remote hosts 5 s, system agent tools 5 s, tool check 10-20 s, docker info
2.5 s, SSH connect 15 s), stream-abort join 5 s, SQLite busy timeouts.

## Host-side (not changed by AutoReiv)

vLLM max_model_len 262144; Spark swap gateway loads a model in about 5 min (its upstream proxy timeout is not
observable); Ollama keep_alive is host-configured (expires_at 2319 = forever); browsers have no fetch timeout;
uvicorn `timeout_keep_alive` 5 s only closes idle keep-alive connections.

## Tests

`tests/unit/kernel/test_card592_relaxed_timeouts.py`, `tests/unit/frontend/card_592_relaxed_timeouts.test.js`, updated
CARD-585/588 and adapter default tests.

## Evidence

- pytest full: 2196 passed, 12 skipped; 1 failure only in the worktree (`test_fleet_coordinator` reads the gitignored
  `notes/homelab` that exists only in the main checkout; passes there). ruff clean. Preflight fast GREEN (vitest 960).
- Live smoke 2026-09-30 on a throwaway :8770 built from this branch (nemotron on Spark, Developer on Nimo qwen3.8), chat
  client with a 60 s socket read timeout and approval POSTs with no client timeout (like a browser):
  - Two hand-offs (Autoreiv -> Developer, approval mode ask): 14 approvals, all answered; the two longest decisions ran the
    child's turn inline for **66.3 s** (write_card) and **64.3 s** (set_card_status) and returned 200 - longer than the
    60 s that used to cut the battery driver.
  - A resumed stream ran about 5 min with 4 keepalive comments; the longest silence on the wire was 15.0 s, so the
    60 s read timeout never fired. No stream errors.
  - Reply limits API on the throwaway: max_seconds 7200, provider_idle_seconds 1800, phase_seconds 21600,
    helper_seconds 1800.
- 2026-09-30: preflight --fast --base qa GREEN. Jacob: merge to qa (small engineering fix). Done; merged into qa.
