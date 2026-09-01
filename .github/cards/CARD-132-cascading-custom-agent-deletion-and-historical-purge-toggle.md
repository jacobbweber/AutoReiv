# [CARD-132] Cascading Custom Agent Deletion and Historical Purge Toggle

> **Status**: In Review
> **Created**: 2026-08-31
> **Spec Reference**: CARD-003; CARD-047; CARD-049; CARD-130
> **Labels**: `type:feat`, `type:ui`, `type:agents`, `type:database`

---

## 1. Why / Intent
When custom agents are deleted from Agent Studio, users need certainty that orphaned database records (e.g. `agent_overrides`, bound routines, lingering pack files) are cleanly removed, while having explicit control over whether historical telemetry, spend accounting, and chat history are preserved for audit purposes or completely purged.

---

## 2. Visual Contract & ASCII Wireframes

### Agent Studio Delete Confirmation Modal (`#deleteAgentModal`)
```text
+--------------------------------------------------------------------------+
| 🗑️ Delete Custom Agent: "Conductor"                                [ ✕ ] |
+--------------------------------------------------------------------------+
| Are you sure you want to permanently delete this custom agent?           |
|                                                                          |
| This will remove the agent configuration and unbind any assigned         |
| routines.                                                                |
|                                                                          |
| [ ] Also permanently purge all chat history and telemetry logs for this  |
|     agent (spend records will be removed from Observability).            |
|                                                                          |
|                                         [ Cancel ]  [ Confirm Delete ]   |
+--------------------------------------------------------------------------+
```

---

## 3. What to Build

### Slice 1: Database Cascading Delete & Purge Methods
- In `src/infrastructure/memory/repositories/settings.py` (and `SQLiteStateStore`):
  - Update `delete_agent_profile(agent_id, purge_history: bool = False) -> bool`:
    1. Delete from `custom_agents` table.
    2. Delete from `agent_overrides` table (`WHERE agent_id = ?`).
    3. Update `agent_routines` table (`UPDATE agent_routines SET agent_id = 'assistant' WHERE agent_id = ?` or clear binding).
    4. If `purge_history=True`:
       - Delete from `chat_sessions` and `messages` matching `agent_id`.
       - Delete from `telemetry_spans` matching `agent_id`.
       - Delete from `agent_turns` matching `agent_id`.
       - Delete from `agent_kpis` matching `agent_id`.
    5. Clean up any pack directory under `$DATA_DIR/packs/<agent_id>`.

### Slice 2: REST Endpoint Parameters
- In `src/web/routers/agents.py`:
  - Update `DELETE /api/agents/{agent_id}`:
    - Accept `purge_history: bool = False` query parameter.
    - Pass `purge_history` to `registry.delete_custom_agent(agent_id, purge_history=purge_history)`.

### Slice 3: Agent Studio UI Modal & Toggle
- In `src/web/templates/index.html`:
  - Add `#deleteAgentModal` with agent name display, `purgeHistoryCheckbox`, cancel button, and confirm delete button.
- In `src/web/static/modules/studios/forge.js`:
  - Update `deleteAgentBtn` click handler to open `#deleteAgentModal`.
  - On confirmation, send `DELETE /api/agents/{id}?purge_history={true|false}`.
  - Show success toast and refresh agent list.

---

## 4. EARS Requirements & Acceptance Criteria

- `[REQ-PURGE-001]` **Cascading Config Deletion**: When a custom agent is deleted (`DELETE /api/agents/{agent_id}`), the state store shall delete its `custom_agents` profile, its `agent_overrides` row, and unbind references from `agent_routines`.
- `[REQ-PURGE-002]` **Purge History Parameter**: When a client invokes `DELETE /api/agents/{agent_id}?purge_history=true`, the backend shall permanently delete all chat sessions, messages, turns, and telemetry spans for that agent.
- `[REQ-PURGE-003]` **Audit Preservation Default**: When `purge_history=false` (default), the backend shall preserve historical telemetry spans and chat sessions for Observability continuity.
- `[REQ-PURGE-004]` **Agent Studio Modal Dialog**: When a user clicks Delete in Agent Studio, a confirmation modal shall prompt for confirmation with a toggle for historical data purge.
- `[REQ-PURGE-005]` **Built-in Protection**: The backend shall strictly reject deletion requests for built-in baseline agents or platform packs (`is_builtin=True` or `is_platform_pack=True`).
- [ ] All automated unit & integration tests pass cleanly via `pytest`.
- [ ] Frontend vitest tests pass cleanly.
- [ ] Zero lint errors via `ruff check .`.
- [ ] Local commit on `qa`. Card status `In Review` after code.

---

## 5. Constraints
- Work on `qa`. Do not push or tag unless explicitly asked.
- Zero breaking changes to built-in agents (`assistant`, `autoreiv`).
- Card stays Ready until Jacob approves build.
