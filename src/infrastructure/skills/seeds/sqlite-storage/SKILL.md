---
name: SQLite Specialty Storage
description: Query and execute operations on private agent SQLite databases with strict security guardrails.
requires_tools:
  - query_agent_database
  - execute_agent_database
---

# SQLite Specialty Storage

Manage structured tabular records in the agent's dedicated private database (`<agent_id>_storage.db`).

## Operating Principles
1. **Isolated Agent Scope**: Every database operation runs strictly against this agent's private SQLite storage file under `$DATA_DIR/packs/<agent_id>/<agent_id>_storage.db`. Cross-agent table access is mechanically isolated.
2. **Read Before Write**: Always inspect the existing schema via `query_agent_database("SELECT name, sql FROM sqlite_master WHERE type='table';")` before authoring tables or updating records.
3. **Parametric & Safe SQL**: Construct deterministic SQL queries. Avoid unindexed Cartesian joins on large datasets.
4. **Structured Output**: Query results return structured JSON rows. Always format summaries concisely for the operator.

## Available Tools
- `query_agent_database(sql, params)`: Execute read-only `SELECT` queries against `<agent_id>_storage.db`.
- `execute_agent_database(sql, params)`: Execute mutating statements (`CREATE TABLE`, `INSERT`, `UPDATE`, `DELETE`) with transactional integrity.

## Done-When
- Schema inspection via `query_agent_database` verifies target table structure.
- Mutating operations via `execute_agent_database` complete with confirmed affected rows.
- All database operations remain strictly bounded to `<agent_id>_storage.db`.

