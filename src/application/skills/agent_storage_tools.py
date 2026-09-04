"""
Agent Storage Tools for isolated private per-agent SQLite databases [CARD-148, REQ-STORAGE-003].
"""

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from src.application.kernel.tool_registry import ScopedToolRegistry, get_tool_context
from src.infrastructure.data.resolver import get_agent_storage_connection


class AgentStorageTools:
    """
    Safe execution and query tools for an agent's dedicated private database.
    """

    def __init__(self, data_dir: Optional[Union[str, Path]] = None) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else None

    def _resolve_target_agent_id(self, agent_id: Optional[str] = None) -> Optional[str]:
        if agent_id and str(agent_id).strip():
            return str(agent_id).strip()
        ctx = get_tool_context()
        caller_id = ctx.get("agent_id")
        if caller_id and str(caller_id).strip():
            return str(caller_id).strip()
        return None

    def query_agent_database(
        self,
        query: str,
        parameters: Optional[List[Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute a read query (SELECT, PRAGMA) against the agent's isolated SQLite database.
        """
        target_id = self._resolve_target_agent_id(agent_id)
        if not target_id:
            return {"status": "error", "error": "Target agent ID not specified and not present in tool context."}

        start_time = time.perf_counter()
        params = parameters if isinstance(parameters, (list, tuple)) else []
        try:
            conn = get_agent_storage_connection(target_id, data_dir=self.data_dir)
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                columns = [desc[0] for desc in cur.description] if cur.description else []
                raw_rows = cur.fetchall()
                rows = [dict(zip(columns, row)) for row in raw_rows]
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return {
                    "status": "success",
                    "agent_id": target_id,
                    "count": len(rows),
                    "rows": rows,
                    "duration_ms": round(duration_ms, 2),
                }
            finally:
                conn.close()
        except sqlite3.Error as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "error",
                "agent_id": target_id,
                "error": str(e),
                "duration_ms": round(duration_ms, 2),
            }

    def execute_agent_database(
        self,
        query: str,
        parameters: Optional[List[Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute DDL or mutation queries (CREATE TABLE, INSERT, UPDATE, DELETE) on the agent's isolated database.
        """
        target_id = self._resolve_target_agent_id(agent_id)
        if not target_id:
            return {"status": "error", "error": "Target agent ID not specified and not present in tool context."}

        start_time = time.perf_counter()
        params = parameters if isinstance(parameters, (list, tuple)) else []
        try:
            conn = get_agent_storage_connection(target_id, data_dir=self.data_dir)
            try:
                cur = conn.cursor()
                cur.execute(query, params)
                conn.commit()
                duration_ms = (time.perf_counter() - start_time) * 1000.0
                return {
                    "status": "success",
                    "agent_id": target_id,
                    "rows_affected": cur.rowcount,
                    "last_insert_id": cur.lastrowid,
                    "duration_ms": round(duration_ms, 2),
                }
            finally:
                conn.close()
        except sqlite3.Error as e:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            return {
                "status": "error",
                "agent_id": target_id,
                "error": str(e),
                "duration_ms": round(duration_ms, 2),
            }

    def register_tools(self, registry: ScopedToolRegistry) -> None:
        registry.register_tool(
            name="query_agent_database",
            description=(
                "Query the agent's private SQLite database. Safe read-only query execution (SELECT, PRAGMA). "
                "Returns rows as structured JSON. Isolated to this agent's private storage."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL query to execute (e.g. 'SELECT * FROM transactions WHERE amount > ?')",
                    },
                    "parameters": {
                        "type": "array",
                        "description": "Optional parameterized query values",
                        "items": {"type": "string"},
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Optional explicit agent ID (defaults to current caller agent)",
                    },
                },
                "required": ["query"],
            },
            handler=self.query_agent_database,
        )

        registry.register_tool(
            name="execute_agent_database",
            description=(
                "Execute schema creation or data modifications (CREATE TABLE, INSERT, UPDATE, DELETE) "
                "in the agent's private SQLite database. Isolated to this agent's private storage."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "SQL statement to execute (e.g. 'CREATE TABLE IF NOT EXISTS notes (id TEXT PRIMARY KEY, content TEXT)')",
                    },
                    "parameters": {
                        "type": "array",
                        "description": "Optional parameterized values",
                        "items": {"type": "string"},
                    },
                    "agent_id": {
                        "type": "string",
                        "description": "Optional explicit agent ID (defaults to current caller agent)",
                    },
                },
                "required": ["query"],
            },
            handler=self.execute_agent_database,
        )
