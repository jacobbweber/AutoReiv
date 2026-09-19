# Requirements Specification: Declarative Agent Pack Lifecycle Reconciliation & Origin Tracking

> **Spec Status**: In Review  
> **Target Release**: Milestone 19  
> **Primary Component**: Agent Architecture, Data Storage & Lifecycle Engine  

---

## 1. Executive Summary & Intent
AutoReiv maintains a strict separation between the repository checkout (factory seed) and user data (`%LOCALAPPDATA%\AutoReiv\`). Previously, seeding was automated via copy-if-missing, but retirement was asymmetric: deleting platform seeds from code left orphaned folders and SQLite records in user data. Without origin tracking, the engine misclassified abandoned platform seeds as user-created custom agents (`(Custom)`), causing ghost resurrections.

This specification introduces:
1. An explicit **`AgentOrigin` taxonomy** (`PLATFORM`, `SYSTEM`, `CUSTOM`) across domain models and SQLite persistence.
2. A **Declarative Desired-State Reconciler** that automatically purges abandoned platform seeds from both disk and database during startup.
3. Strict protection for **`CUSTOM` user agents**, ensuring operator-authored agents are never touched by platform sync.

---

## 2. User Stories & EARS Functional Requirements

### [REQ-RECON-001]: Agent Origin Taxonomy & Schema Migration
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL define an AgentOrigin enum with values PLATFORM, SYSTEM, and CUSTOM, add an origin field to AgentProfile, and add an origin column to custom_agents and agent_overrides tables defaulting to CUSTOM for legacy rows.`
- **Acceptance Criteria**:
  - [ ] Given `AgentOrigin`, it must support serialization to and from lowercase string literals: `"platform"`, `"system"`, `"custom"`.
  - [ ] Given `AgentProfile`, it must expose `origin: AgentOrigin = AgentOrigin.CUSTOM`.
  - [ ] Given `SQLiteConnectionManager._migrate_if_missing`, it must add `origin TEXT NOT NULL DEFAULT 'custom'` to `custom_agents` and `agent_overrides` if missing.

### [REQ-RECON-002]: Declarative Desired-State Reconciler
- **Type**: Event-Driven
- **EARS Statement**: `WHEN AutoReiv bootstraps on startup THE SYSTEM SHALL execute DeclarativePackReconciler comparing desired PLATFORM_PACK_IDS against actual AppData state, automatically pruning any platform-origin agent or retired pack from both the filesystem and SQLite database.`
- **Acceptance Criteria**:
  - [ ] Given `DeclarativePackReconciler.reconcile()`, any agent profile in SQLite with `origin == AgentOrigin.PLATFORM` whose `id` is not in `PLATFORM_PACK_IDS` must be deleted from `custom_agents` and `agent_overrides`.
  - [ ] Given any directory under `$DATA_DIR/packs/<id>` whose ID is in `RETIRED_PLATFORM_PACK_IDS` or represents an obsolete platform seed, it must be pruned from disk.
  - [ ] Given the startup sequence, `DeclarativePackReconciler.reconcile()` must execute before any pack tools or agents are mounted.

### [REQ-RECON-003]: User Custom Agent Invariant & Boundary Protection
- **Type**: Unwanted Behavior
- **EARS Statement**: `IF an agent profile has origin == AgentOrigin.CUSTOM THEN THE SYSTEM SHALL NEVER delete or overwrite the agent pack folder or database records during platform sync or reconciliation.`
- **Acceptance Criteria**:
  - [ ] Given a custom agent created in Agent Studio (`origin == AgentOrigin.CUSTOM`), running `DeclarativePackReconciler.reconcile()` must leave its files and database rows untouched.
  - [ ] Given a custom agent with a custom database (`<id>_storage.db`), reconciliation must preserve the database.

### [REQ-RECON-004]: Ghost Import Loop Elimination
- **Type**: Ubiquitous
- **EARS Statement**: `THE SYSTEM SHALL prevent automatic re-import of unmanaged or retired pack directories into SQLite during startup unless explicitly marked as user_managed in pack.json or imported through Studio.`
- **Acceptance Criteria**:
  - [ ] Given an orphaned folder under `$DATA_DIR/packs/` without `user_managed: true` or valid custom manifest, `install_platform_agent_packs` must not re-import it into SQLite.

### [REQ-RECON-005]: API Exposure & Origin-Aware Studio Roster
- **Type**: State-Driven
- **EARS Statement**: `WHILE Agent Studio queries /api/agents THE SYSTEM SHALL return the origin attribute for every agent profile, rendering platform agents as (Platform) and custom agents as (Custom) with delete actions restricted to custom agents.`
- **Acceptance Criteria**:
  - [ ] Given `GET /api/agents`, every payload includes `"origin": "platform" | "system" | "custom"`.
  - [ ] Given `DELETE /api/agents/{id}`, requests targeting `origin == "platform"` or `origin == "system"` return HTTP 403 / 400.

---

## 3. Boundary & Non-Functional Constraints
- **Idempotence**: Running reconciliation repeatedly must produce the exact same clean state with zero errors.
- **Zero Loss**: User-created agents, custom memories, and notes must never be deleted by platform updates.
- **Backward Compatibility**: Existing databases with un-tagged rows must migrate cleanly without schema exceptions.
