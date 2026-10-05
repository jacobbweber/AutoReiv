---
id: CARD-602
title: "Owner-only routes accept requests from any website origin; add an Origin/Host check"
type: security
status: In Review
priority: P2
milestone: M24
needs_decision: none
proof:
  journeys: [card-602-origin-guard]
  checks: [tests/unit/web/test_card602_origin_guard.py, tests/unit/frontend/card602_allowed_origins.test.js]
branch: feat/card-602-owner-routes-origin-check
log: {minutes: 45, qa_runs: 1, findings: 0}
created: 2026-10-01
related:
  - CARD-578
labels:
  - type:security
  - area:web
  - area:security
  - P2
---

# [CARD-602] Owner-only routes accept requests from any website origin; add an Origin/Host check

> **Status**: In Review (2026-10-05, branch `feat/card-602-owner-routes-origin-check`, not merged). Moved from findings (CARD-578), 2026-09-29.

## Why
The app is unauthenticated and CORS allowed any origin (`allow_origins=["*"]`). A web page open in Jacob's browser could call owner-only routes (for example runtime tool enable/disable).

## Built
- `src/web/origin_guard.py`: `OriginGuardMiddleware` rejects POST/PUT/PATCH/DELETE when `Origin` (or `Referer` origin) is present and not the request Host / configured extras. No Origin (curl, scripts) stays allowed. `SettingsAwareCORSMiddleware` narrows CORS to localhost, loopback, RFC1918 LAN, TestClient, plus extras from settings (re-read each request).
- Setting `allowed_origins` via GET/PUT `/api/settings/allowed-origins`; Settings > Data > Allowed browser origins (one URL per line).
- `app.js?v=2.0.109`.

## Plan and decisions
- Check Origin on mutating methods only; GETs stay open (no secrets in get responses that need CSRF for this card).
- Extras are absolute http(s) origins; bad values return 400. LAN regex covers 10/8, 172.16/12, 192.168/16 without listing every host.
- Engineering: no new dependencies.

## Results
| Check | Result | Notes |
|---|---|---|
| Unit origin helper + middleware (14) | PASS | evil Origin 403; no Origin / self Origin not blocked by guard; GET with evil Origin 200; extras setting; CORS preflight |
| Vitest field parser (2) | PASS | |
| Full pytest | PASS | 2528 passed / 12 skipped |
| Release preflight | PASS | GREEN; vitest 1054; smoke 83/83 |
| Live :8770 (throwaway, Spark Nemotron verified first) | PASS | POST `/api/tools/native/.../disable` Origin evil -> 403; no Origin / self Origin -> 404 (tool missing, not guard); GET health with evil Origin -> 200; Settings saved `https://phone.example:8443` then that Origin -> 404 not 403 |

Screenshots: `autoreiv-qa\sprint1005\602-settings-allowed-origins-{desktop,saved-desktop,phone}.png`

## Findings
- None new.

## Release note
Other websites can no longer call AutoReiv from your browser; only this PC, your LAN, and any extra origins you list in Settings are allowed.
