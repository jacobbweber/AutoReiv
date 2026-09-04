# [CARD-148] Per-Agent Persistent Storage in Agent Studio and Pack SDK

> **Status**: In Review
> **Created**: 2026-09-03
> **Spec Reference**: none
> **Labels**: `type:feature`, `AutoReiv.Web`, `AutoReiv.Kernel`, `AutoReiv.Memory`

---

## 1. Why / Intent

Specialist agents (such as a finance tracker, inventory manager, or structured logging assistant) need to maintain structured records across sessions without mixing their private data into AutoReiv's central system database or other agents' memories. 

All agent artifacts (isolated SQLite database, workflows, and skills) should live directly inside the agent's pack directory (`$DATA_DIR/packs/<agent_id>/`), ensuring complete lifecycle parity during backup, export, and deletion.

Additionally, AutoReiv's central system database should live under a dedicated directory (`$DATA_DIR/database/autoreiv.db`) rather than bare at the data directory root, keeping the top-level directory clean and unambiguous.

---

## 2. What to Build

1. **Central Database Relocation (`src/infrastructure/data/resolver.py`, `backup.py`)**:
   - Resolve central system database to `$DATA_DIR/database/autoreiv.db`.
   - On startup, automatically migrate any existing `$DATA_DIR/autoreiv.db` (along with `-wal` and `-shm`) into `$DATA_DIR/database/autoreiv.db` so existing user state is never lost.
   - Update backup and restore routines to support the `database/autoreiv.db` path while remaining compatible with older backup archives.
2. **Pack-Scoped Storage & Workflow Directory Layout (`resolver.py`, `workflows.py`, `agents.py`)**:
   - Resolve agent persistent storage to `$DATA_DIR/packs/<agent_id>/storage.db`.
   - Eagerly provision and initialize the SQLite database on save when `storage_enabled` is checked.
   - Update `WorkflowStore` to write workflows under `$DATA_DIR/packs/<agent_id>/workflows/`, while seamlessly reading any legacy workflows from `$DATA_DIR/agents/<agent_id>/workflows/`.
3. **Domain Model & Pack Schema (`src/domain/kernel/models.py`, `schema.py`, `service.py`)**:
   - Support `storage_enabled: bool` and `storage_type: str = "sqlite"` in `AgentProfile` and `pack.json`.
   - Preserve storage settings during pack export, import, and scaffolding.
4. **Agent Studio Roster Sheet UI (`src/web/templates/index.html`, `forge.js`)**:
   - Checkbox: `Persistent Storage` (`#forgeStorageEnabled`)
   - Selector: `Database Type` (`#forgeStorageType`) with option `SQLite (Isolated File)`
   - Explanatory label pointing to `$DATA_DIR/packs/<agent_id>/storage.db`.
5. **Agent Storage Tools (`src/application/skills/agent_storage_tools.py`)**:
   - `query_agent_database`: Read-only queries against `$DATA_DIR/packs/<agent_id>/storage.db`.
   - `execute_agent_database`: DDL & data mutations on `$DATA_DIR/packs/<agent_id>/storage.db`.

---

## 3. Acceptance Criteria (Definition of Done)

- [x] `[REQ-STORAGE-001]`: `AgentProfile` and `pack.json` support `storage_enabled` and `storage_type` configuration.
- [x] `[REQ-STORAGE-002]`: Agent Studio roster sheet displays a `Persistent Storage` checkbox and `Database Type` selector wired to `/api/agents/{id}`.
- [x] `[REQ-STORAGE-003]`: Storage-enabled agents have an isolated SQLite database created at `$DATA_DIR/packs/{agent_id}/storage.db`.
- [x] `[REQ-STORAGE-004]`: AutoReiv's central system database lives under `$DATA_DIR/database/autoreiv.db` with auto-migration from `$DATA_DIR/autoreiv.db`.
- [x] `[REQ-STORAGE-005]`: Agent Pack export and import preserve the persistent storage configuration.
- [x] `[REQ-STORAGE-006]`: Automated unit and integration tests pass cleanly via `pytest` and `vitest`.
- [x] `[REQ-STORAGE-007]`: Zero linting errors via `ruff check .` and frontend static analysis.

---

## 4. Constraints & Honor Flags

- Zero breaking changes to existing agent profiles or central `autoreiv.db`.
- Agents without storage enabled incur zero overhead and do not create storage files.
- Local `qa` branch is source of truth.
- Follow "How we walk cards with Jacob" rules.
