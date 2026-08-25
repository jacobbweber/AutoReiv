# [CARD-047] Agent Chat History Retention and Automated Session Cleanup

> **Status**: Ready (Backlog / Future Work)
> **Created**: 2026-08-25
> **Spec Reference**: docs/specs/agent-session-history-retention/ (to be drafted when active)
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
Over time, active agents accumulate dozens or hundreds of conversational chat sessions in SQLite. Users need a granular, per-agent retention setting (e.g., keep history for 7 days, 14 days, 30 days, or indefinitely) to automatically prune stale conversation threads from the UI history sidebar.

> [!IMPORTANT]
> **Strict Memory Isolation Invariant**:
> This feature is **strictly scoped to transient chat session history and message records** (`sessions` and `messages` SQLite tables).
> It **MUST NOT** purge or impact long-term semantic knowledge, episodic fact memory (`memory_facts`), or wiki documents.

---

## 2. What to Build

1. **Domain Model Extension**:
   - Add optional `history_retention_days: Optional[int] = None` (where `None` or `0` means keep indefinitely) to `AgentProfile` (`src/domain/kernel/models.py`) and `AgentCustomization` (`src/domain/settings/models.py`).
2. **SQLite State Store Pruning Engine**:
   - Implement `prune_expired_sessions(agent_id: Optional[str] = None, max_age_days: Optional[int] = None) -> int` in `SQLiteStateStore` (`src/infrastructure/memory/sqlite_store.py`).
   - Cascading removal of expired `sessions` and their associated `messages` records based on `updated_at < now() - interval 'X days'`.
3. **Automated Background Pruning Routine**:
   - Automated retention cleanup hook executed either periodically in `RoutineScheduler` / `SQLiteStateStore` startup or on agent turn completion.
4. **Agent Studio UI Retention Controls**:
   - In Agent Studio (`src/web/static/modules/studios/agents.js` and `index.html`), provide a dedicated **"Chat History Retention"** dropdown / numeric field per agent (Options: `Keep Forever`, `3 Days`, `7 Days`, `14 Days`, `30 Days`, `90 Days`, `Custom...`).
   - In Chat Studio (`src/web/static/modules/studios/chat.js`), respect pruned sessions and refresh conversation list cleanly.

---

## 3. Visual UI Contract (ASCII Wireframe)

```text
+-------------------------------------------------------------------------+
| [🤖 Agent Studio] - Edit Agent: Linux Sysadmin                         |
|-------------------------------------------------------------------------|
| Agent Name:    [ Linux Sysadmin                                      ]  |
| Model Purpose: [ Task Execution v ]    Model: [ ollama/qwen2.5:7b v ]   |
| System Tone:   [ Technical      v ]                                     |
|                                                                         |
| [⚙️ Session & History Management]                                       |
| Chat Session Retention: [ 7 Days (Auto-cleanup)                     v ] |
|   (i) Automatically purges chat threads older than 7 days.              |
|       Does NOT affect episodic memory or saved wiki notes.              |
|                                                                         |
| Allowed Skills / Tools:                                                 |
| [x] cli_exec  [x] system_info  [ ] task_tracker  [ ] delegate_task        |
|                                                                         |
| [ 💾 Save Agent Profile ]       [ 🗑️ Prune Old Sessions Now ]         |
+-------------------------------------------------------------------------+
```

---

## 4. Acceptance Criteria (Definition of Done)

- [ ] **[REQ-RET-001] Model & Schema Extension**: `AgentProfile` and `AgentCustomization` support `history_retention_days` (`int >= 0` or `None`).
- [ ] **[REQ-RET-002] SQLite Session Pruning Engine**: `SQLiteStateStore.prune_expired_sessions` correctly deletes expired sessions and messages matching the retention threshold without foreign key or WAL deadlocks.
- [ ] **[REQ-RET-003] Memory Isolation Guarantee**: Verifies 0 deletions from `memory_facts`, `wiki`, `telemetry_spans`, or active routines during session history pruning.
- [ ] **[REQ-RET-004] Background & Triggered Execution**: Pruning runs automatically based on configured agent policies or via maintenance trigger.
- [ ] **[REQ-RET-005] REST Configuration & Pruning API**: `PATCH /api/agents/{agent_id}/settings` updates retention, and `POST /api/agents/{agent_id}/history/prune` triggers immediate manual cleanup.
- [ ] **[REQ-RET-006] Agent Studio UI Retention Controls**: Agent Studio UI includes retention select/input with persistence to SQLite.
- [ ] Automated tests green via `pytest` (backend unit + store tests) and `vitest` (frontend controls).
- [ ] Zero lint errors via `ruff check .` and `npm run lint:frontend`.

---

## 5. Constraints & Honor Flags
- Standard honor constraints apply.
- Zero breaking changes to existing passing tests.
- Single isolated `feat/*` branch cut from `qa` when work begins.

