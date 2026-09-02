---
id: CARD-134
title: "Control Plane Focus: Dashboard Experiment Retirement & Clean Agent State"
status: In Review
priority: High
created: 2026-09-02
owner: Antigravity
description: "Retires experimental dynamic dashboard renderer and custom pack UI tabs to preserve AutoReiv's core focus as a high-performance Multi-Agent Control Plane. Cleans up deleted agent artifacts, stale SDLC pack schemas, and purges retired agent telemetry."
---

# CARD-134: Control Plane Focus — Dashboard Experiment Retirement & Clean Agent State

## 1. Context & Motivation
AutoReiv's primary mission is a local-first **Multi-Agent Control Plane** (Orchestration, Agent & Skill Studio, Knowledge Vault / Wiki, HITL Action Approvals, and Tool Execution). Domain-specific user applications (such as gardening portals or bespoke developer dashboards) belong in separate standalone applications that interface with AutoReiv via REST API / MCP.

This card cleanly retires the experimental `dashboard.json` dynamic studio renderer (CARD-133) and removes custom pack artifacts (`nexus-code-architect`, `gardening`), while **preserving all critical engine enhancements** (model purpose slot inheritance, skill tool binding, and HITL approval resume fixes).

## 2. Invariants & Scope
- **Primitives**: Remain strictly **Agent**, **Skill** (`SKILL.md`), and **Tool** (one callable).
- **Preserved Fixes**:
  - Model resolution & Purpose Matrix slot inheritance.
  - Automatic skill-tool binding in `scaffold_pack`.
  - HITL tool call ID preservation and in-place message history update.
  - Cascading agent deletion and telemetry purge toggle.
- **Retired / Cleaned**:
  - `AgentDashboardManifest` and `dashboard` fields from `pack.json` schemas.
  - `dynamic_studio.js` and `#view-dynamic` from web frontend.
  - Dashboard REST endpoints (`/api/agent-packs/dashboards`, `/action`).
  - Stale `agent-packs/nexus-code-architect` and `agent-packs/gardening` directories and user data dir artifacts.
  - Purge of telemetry records, sessions, and messages associated with deleted agents.

## 3. Vertical Slices

### Slice 1: Schema & Core Engine Cleanup
- Remove dashboard models from `src/application/agent_packs/schema.py`.
- Remove dashboard methods from `AgentPackService` (`src/application/agent_packs/service.py`).
- Remove `scaffold_agent_dashboard` and `read_agent_dashboard` from `AgentBuilderTools` and `platform-packs/autoreiv/pack.json`.

### Slice 2: Web API & Frontend Cleanup
- Remove dashboard routes (`/api/agent-packs/dashboards`, `/action`) from `src/web/routers/agents.py`.
- Remove `#view-dynamic` from `src/web/templates/index.html`.
- Remove `dynamic_studio.js` from `src/web/static/modules/studios/`.
- Remove dynamic studio initialization and tab event listeners from `src/web/static/app.js`.

### Slice 3: State & Artifacts Cleanup
- Delete `agent-packs/nexus-code-architect/` and `agent-packs/gardening/` from repo.
- Purge any remaining disk directories in user packs (`%LOCALAPPDATA%\AutoReiv\packs\*`).
- Purge telemetry spans, sessions, messages, and approvals for `nexus-code-architect` and `gardening` in the SQLite store.
- Update runbooks in `build-agent-pack/SKILL.md`.

### Slice 4: Verification & DoD Pre-flight
- 100% green unit and integration tests (Pytest + Vitest).
- Clean lint and typecheck.
