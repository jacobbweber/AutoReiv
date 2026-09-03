# [CARD-148] Per-Agent Persistent Storage in Agent Studio and Pack SDK

> **Status**: Ready
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory`

---

## 1. Why / Intent

Specialist agents (such as a finance tracker, inventory manager, or structured logging assistant) need to maintain structured records across sessions without mixing their private data into AutoReiv's central system database or other agents' memories. 

Users need a simple toggle on the agent's roster sheet in Agent Studio to enable persistent storage, select an isolated database engine (starting with a lightweight SQLite database file per agent), and have this capability packaged cleanly into the Agent Pack SDK (`pack.json`).

---

## 2. What to Build

1. **Domain Model & Pack Schema (`src/domain/kernel/models.py`, `docs/agent-packs.md`)**:
   - Add storage fields to `AgentProfile`:
     - `storage_enabled: bool = False`
     - `storage_type: str = "sqlite"` (lightweight file-based SQLite database)
   - Update `pack.json` schema to serialize/deserialize storage settings:
     ```json
     {
       "storage": {
         "enabled": true,
         "type": "sqlite"
       }
     }
     ```
2. **Agent Studio Roster Sheet UI (`src/web/templates/index.html` & `agent_studio.js`)**:
   - In Agent Studio (View 4), inside the identity or execution settings panel, add a **Persistent Storage** control:
     - Checkbox: `Persistent Storage` (`#forgeStorageEnabled`)
     - Selector: `Database Type` (`#forgeStorageType`) with option `SQLite (Isolated File)`
     - Short explanatory label: *"Provisions a dedicated, isolated database file for this agent under its data directory."*
   - Wire form loading, saving (`PUT /api/agents/{id}`), and pack export/import to persist these values.
3. **Storage Provisioning & Database Resolution (`src/infrastructure/data/resolver.py`, `src/infrastructure/memory/`)**:
   - When an agent has storage enabled, resolve and lazily create an isolated SQLite database file at `$DATA_DIR/agents/<agent_id>/storage.db`.
   - Provide an isolated connection helper so tools can safely execute queries against the agent's dedicated database without touching `autoreiv.db`.
4. **Agent Storage Tools (`src/application/tools/` or `src/application/skills/`)**:
   - Provide platform tools available to storage-enabled agents:
     - `query_agent_database`: Run read queries against the agent's isolated database.
     - `execute_agent_database`: Execute schema migrations or data mutations (INSERT, UPDATE, CREATE TABLE).

---

## 3. Acceptance Criteria (Definition of Done)

- [ ] `[REQ-STORAGE-001]`: `AgentProfile` and `pack.json` support `storage_enabled` and `storage_type` configuration.
- [ ] `[REQ-STORAGE-002]`: Agent Studio roster sheet displays a `Persistent Storage` checkbox and `Database Type` selector that reads and writes via `/api/agents/{id}`.
- [ ] `[REQ-STORAGE-003]`: Storage-enabled agents have an isolated SQLite database created at `$DATA_DIR/agents/{agent_id}/storage.db`.
- [ ] `[REQ-STORAGE-004]`: Agent Pack export and import preserve the persistent storage configuration.
- [ ] `[REQ-STORAGE-005]`: Automated unit and integration tests pass cleanly via `pytest`.
- [ ] `[REQ-STORAGE-006]`: Zero linting errors via `ruff check .` and frontend static analysis.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing agent profiles or central `autoreiv.db`.
- Agents without storage enabled incur zero overhead and do not create storage files.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
