---
id: CARD-602
title: "Owner-only routes accept requests from any website origin; add an Origin/Host check"
status: Ready
created: 2026-10-01
branch: qa
related:
  - CARD-578
labels:
  - type:security
  - area:web
  - area:security
  - P2
needs_decision: none
milestone: M24
---

# [CARD-602] Owner-only routes accept requests from any website origin; add an Origin/Host check

> **Status**: Ready (filed 2026-10-01)
> **Labels**: `type:security`, `area:web`, `area:security`, `P2`

## Why

Moved from docs/findings.md (2026-09-29, CARD-578). The app is unauthenticated and CORS allows any origin (`allow_origins=["*"]`). A web page open in Jacob's browser could therefore call owner-only routes, for example runtime tool enable/disable. Jacob parked the Origin check on 2026-09-29; it is filed so it stays tracked.

## Scope

1. A small middleware for state-changing requests (POST/PUT/PATCH/DELETE): reject a request whose `Origin` (or `Referer`) is present and not the app's own host or a configured LAN host. Requests without an Origin (curl, scripts) stay allowed.
2. Narrow CORS to the same hosts.
3. A setting for extra allowed origins (for example a phone reverse proxy).

## Acceptance criteria

- **Integration:** a POST to `/api/tools/native/...` with `Origin: https://evil.example` returns 403. The same request from the app's origin, or without an Origin, works.
- The UI works from `127.0.0.1:8000` and `192.168.1.99:8000` (smoke + phone check).
- Fast preflight and smoke are green.
