# [CARD-222] Steering Truth Sync (Roadmap / Product / OpenAPI / PROJECT.md)

> **Status**: Done
> **Created**: 2026-09-10
> **Spec Reference**: Design marathon anti-theatre docs; follow-on to CARD-037 drift
> **Labels**: `type:docs`, `AntiTheatre`

---

## 1. The Three Beats

### Beat 1: What Jacob Means
Steering and packaging metadata must match shipped reality. No Docs Studio theatre, no open Milestones that already shipped, no OpenAPI version stuck on 0.15.0 while the package is 0.28.0.

### Beat 2: What AutoReiv Does Now
- `steering/roadmap.md` still shows M15–M17 unchecked despite MCP, external verifier/Reflexion, and standing Job-Graph (CARD-215..221).
- `steering/product.md` claims **Docs Studio (`docs.js`)** but no `docs.js` studio ships (Studios: chat/factory/forge/observability/projects/prompts/routines/settings/skills/wiki).
- FastAPI OpenAPI `version` is `0.15.0` while `pyproject.toml` / `package.json` / `/api/health` report `0.28.0`.
- Root `PROJECT.md` is a stale early audit brief that reads like current product truth.

### Beat 3: What Will Change
Docs-only truth sync on `feat/*`: roadmap M15–17 Done/Superseded, product.md Docs Studio corrected, OpenAPI version aligned to package, brief PROJECT.md stale warning. No merge qa/main.

---

## 2. Acceptance Criteria (Definition of Done)

- [x] Roadmap M15–17 reflect Done / Superseded reality (not open theatre).
- [x] product.md does not claim a shipped Docs Studio (`docs.js`) that is absent.
- [x] OpenAPI FastAPI version matches package `0.28.0`.
- [x] PROJECT.md carries an explicit stale-audit warning pointing operators to steering + CHANGELOG.
- [x] Push `feat/*` only — never qa/main.

---

## 3. Constraints & Honor Flags

- Docs/metadata only (plus OpenAPI version string alignment).
- Branch: `feat/standing-job-graph-runtime`. Never push qa/main.
- Anti-theatre: status language must name what superseded Goal-mode / Docs Studio claims.

