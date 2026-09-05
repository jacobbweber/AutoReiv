# [CARD-161] Chat Options Drawer Context Tokens, Manual Compaction, and Loaded Tools Inspector

> **Status**: In Review
> **Created**: 2026-09-05
> **Spec Reference**: none
> **Labels**: `type:feature`, `needs-triage`

---

## 1. Why / Intent
In Chat Studio (`#navChat`), tapping the `+` Options button (`#chatOptionsToggleBtn`) slides open the Chat Options Drawer (`#chatOptionsDrawer`). Currently, the user has no visibility into how much of the model's context window has been consumed by the active conversation, nor can they trigger early context compaction without waiting for an automated overflow during a turn. Additionally, the user cannot see what tools are loaded for the active agent without navigating away to Agent Studio.

The user wants two new sections in the options drawer:
1. **Context Window & Compaction**: Shows estimated tokens used / total available (e.g. `2,150 / 32,768 (7%)`) with a visual meter and a **`Compact`** button (`#chatManualCompactBtn`) to compact history early.
2. **Loaded Tools & Inspector**: Shows a summary badge (`5 tools loaded`) and a **`View Tools`** button (`#chatViewToolsBtn`) that opens a lightweight popup/modal showing all tools and their descriptions.

---

## 2. What to Build

### A. Backend Endpoints (`src/web/routers/chat.py`)
1. `GET /api/sessions/{session_id}/context`:
   - Calculates current session token usage using `ContextCompactor.estimate_tokens` on session messages and system prompt.
   - Resolves the active model context limit (from agent `context_window` override or model default).
   - Resolves all tools authorized for this agent from `tool_registry.get_tools_for_agent(agent)`.
   - Returns:
     ```json
     {
       "session_id": "...",
       "agent_id": "finance",
       "used_tokens": 2150,
       "max_tokens": 32768,
       "percent_used": 6.6,
       "tools_count": 5,
       "tools": [
         {"name": "read_document_file", "description": "..."},
         {"name": "query_agent_database", "description": "..."}
       ]
     }
     ```
2. `POST /api/sessions/{session_id}/compact`:
   - Compacts the session history using `ContextCompactor.compact_with_stats`.
   - Replaces earlier turns in SQLite with the compacted summary turn (preserving root intent and recent turns).
   - Returns updated token metrics (`compacted_tokens`, `turns_compacted`, `used_tokens`, `max_tokens`).

### B. Chat Options Drawer UI (`src/web/templates/index.html`)
Inside `#chatOptionsDrawer`, add two dedicated sections:
1. **Context Budget Section**:
   - Header: `Context Budget` with badge `#chatContextTokensBadge` (`2,150 / 32,768`).
   - Compact progress bar `#chatContextProgressBar` showing percent consumed.
   - `[ 🧹 Compact ]` button (`#chatManualCompactBtn`) with tooltip "Compact earlier turns into a summary to free context".
2. **Active Tools Section**:
   - Header: `Active Tools` with badge `#chatToolsCountBadge` (`5 tools loaded`).
   - `[ 👁️ View Tools ]` button (`#chatViewToolsBtn`).
3. **Loaded Tools Inspector Modal (`#chatToolsModal`)**:
   - Clean, lightweight dialog showing the list of active tools with their names and descriptions.
   - Search filter to quickly filter tools.
   - Close on `[ ✕ ]`, outside click, or `Escape`.

### C. Frontend Wiring (`src/web/static/modules/studios/chat.js`)
- When `#chatOptionsDrawer` opens, asynchronously query `/api/sessions/{session_id}/context` and update the token meter and tool count badge.
- Clicking `#chatManualCompactBtn` calls `POST /api/sessions/{session_id}/compact`, shows toast notification with token savings, and re-renders messages.
- Clicking `#chatViewToolsBtn` renders the loaded tools in `#chatToolsModal`.

---

## 3. Wireframes

### Chat Options Drawer (`#chatOptionsDrawer`)
```text
+-------------------------------------------------------------+
| ⚙️ Chat Modes & Options                                  [ ✕ ]|
+-------------------------------------------------------------+
| RUNTIME MODES:                                              |
| [ ✓ Verify ]       [ 🎯 Goal Mode ]       [ ⚡ Auto-run ]    |
|                                                             |
| WORKFLOW PRESET:                                            |
| [ 🔀 Select Workflow...                                 v ] |
|                                                             |
| CONTEXT BUDGET:                                             |
| [ 2,150 / 32,768 tokens (7%) ]              [ 🧹 Compact ]  |
| [====-----------------------------------------------------] |
|                                                             |
| ACTIVE TOOLS:                                               |
| [ 5 tools loaded for Personal Finance Lead ] [ 👁️ View Tools]|
|                                                             |
| [ 📎 Attach File ]   [ ✨ Quick Prompts ]                    |
+-------------------------------------------------------------+
```

### Loaded Tools Inspector Modal (`#chatToolsModal`)
```text
+-------------------------------------------------------------+
| 🛠️ Active Tools (Personal Finance Lead - 5 tools)        [ ✕ ]|
+-------------------------------------------------------------+
| [ 🔍 Filter tools...                                      ] |
|                                                             |
| • read_document_file                                        |
|   Read, extract, and analyze content from documents (PDF,   |
|   Excel, CSV, Word, text).                                  |
|                                                             |
| • query_agent_database                                      |
|   Execute a read query (SELECT, PRAGMA) against private DB. |
|                                                             |
| • execute_agent_database                                    |
|   Execute a write statement (INSERT, UPDATE) against DB.    |
|                                                             |
| • log_transactions                                          |
|   Ingests transaction records and parses bank CSV exports.  |
|                                                             |
| • summarize_finances                                        |
|   Computes cashflow metrics, budgets, and savings velocity. |
+-------------------------------------------------------------+
```

---

## 4. Acceptance Criteria (Definition of Done)
- [x] `GET /api/sessions/{session_id}/context` accurately computes token count and returns loaded tools.
- [x] `POST /api/sessions/{session_id}/compact` executes `ContextCompactor.compact_with_stats`, replaces old turns in SQLite, and returns updated metrics.
- [x] Options drawer displays `Context Budget` with live tokens used / max tokens and progress bar.
- [x] Options drawer displays `Active Tools` with count of loaded tools.
- [x] Clicking `Compact` compacts the session history and updates the token meter immediately.
- [x] Clicking `View Tools` displays `#chatToolsModal` with all authorized tool names and descriptions.
- [x] Unit and frontend integration tests pass cleanly via `pytest` and `vitest`.
- [x] Zero lint errors via `ruff check .` and `npm run lint:frontend`.
