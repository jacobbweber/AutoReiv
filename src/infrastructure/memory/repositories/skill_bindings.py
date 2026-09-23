"""Operational SQLite skill→tool bindings [CARD-411 / ADR-0056 Hybrid C+].

SQLite is the sole live writer for which catalog tools a skill requires.
AppData pack.json is not a second source of truth for these bindings.
"""

from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional, Sequence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS skill_binding_meta (
            skill_id TEXT PRIMARY KEY,
            tier TEXT NOT NULL DEFAULT 'pack',
            safety_json TEXT NOT NULL DEFAULT '{}',
            user_modified INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS skill_tool_bindings (
            skill_id TEXT NOT NULL,
            tool_id TEXT NOT NULL,
            position INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (skill_id, tool_id)
        );
        CREATE INDEX IF NOT EXISTS idx_skill_tool_bindings_tool ON skill_tool_bindings(tool_id);
        """
    )


def operational_db_path(explicit: Optional[str] = None) -> Optional[str]:
    if explicit:
        return explicit
    env_path = os.environ.get("AUTOREIV_DB_PATH")
    if env_path:
        return env_path
    try:
        from src.infrastructure.data.resolver import DataDirResolver

        return str(DataDirResolver().resolve().db_path)
    except Exception:
        return None


class SkillToolBindingRepository:
    """Replace-all bindings for one skill. Empty tool lists still persist a meta row."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = operational_db_path(db_path)

    def _connect(self) -> Optional[sqlite3.Connection]:
        path = self.db_path
        if not path or path == ":memory:":
            return None
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000;")
        return conn

    def replace(
        self,
        skill_id: str,
        tool_ids: Sequence[str],
        *,
        tier: str = "pack",
        safety: Optional[Mapping[str, Any]] = None,
    ) -> dict[str, Any]:
        clean_id = (skill_id or "").strip()
        if not clean_id:
            raise ValueError("skill_id is required")
        tools = [str(item).strip() for item in tool_ids if str(item).strip()]
        safety_payload = {
            "read_only": bool((safety or {}).get("read_only", False)),
            "requires_hitl": bool((safety or {}).get("requires_hitl", False)),
            "untrusted_input_allowed": bool((safety or {}).get("untrusted_input_allowed", False)),
        }
        conn = self._connect()
        if conn is None:
            raise RuntimeError("Operational SQLite path is not configured for skill bindings.")
        stamp = _now()
        try:
            _ensure_schema(conn)
            conn.execute("DELETE FROM skill_tool_bindings WHERE skill_id = ?", (clean_id,))
            for index, tool_id in enumerate(tools):
                conn.execute(
                    """
                    INSERT INTO skill_tool_bindings (skill_id, tool_id, position, updated_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (clean_id, tool_id, index, stamp),
                )
            conn.execute(
                """
                INSERT INTO skill_binding_meta (skill_id, tier, safety_json, user_modified, updated_at)
                VALUES (?, ?, ?, 1, ?)
                ON CONFLICT(skill_id) DO UPDATE SET
                    tier = excluded.tier,
                    safety_json = excluded.safety_json,
                    user_modified = 1,
                    updated_at = excluded.updated_at
                """,
                (clean_id, tier or "pack", json.dumps(safety_payload), stamp),
            )
            conn.commit()
        finally:
            conn.close()
        return self.get(clean_id) or {
            "skill_id": clean_id,
            "tier": tier or "pack",
            "safety": safety_payload,
            "requires_tools": tools,
            "user_modified": True,
        }

    def delete(self, skill_id: str) -> None:
        """Drop binding rows for one skill. The skill store delete calls this."""
        clean_id = (skill_id or "").strip()
        if not clean_id:
            return
        conn = self._connect()
        if conn is None:
            return
        try:
            _ensure_schema(conn)
            conn.execute("DELETE FROM skill_tool_bindings WHERE skill_id = ?", (clean_id,))
            conn.execute("DELETE FROM skill_binding_meta WHERE skill_id = ?", (clean_id,))
            conn.commit()
        finally:
            conn.close()

    def get(self, skill_id: str) -> Optional[dict[str, Any]]:
        found = self.tools_for_skills([skill_id])
        clean_id = (skill_id or "").strip()
        if clean_id not in found:
            return None
        meta = self._meta_for([clean_id]).get(clean_id) or {}
        return {
            "skill_id": clean_id,
            "tier": meta.get("tier") or "pack",
            "safety": meta.get("safety") or {},
            "requires_tools": list(found[clean_id]),
            "user_modified": True,
        }

    def _meta_for(self, skill_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
        ids = [str(item).strip() for item in skill_ids if str(item).strip()]
        if not ids:
            return {}
        conn = self._connect()
        if conn is None:
            return {}
        try:
            _ensure_schema(conn)
            placeholders = ",".join("?" for _ in ids)
            rows = conn.execute(
                f"SELECT skill_id, tier, safety_json FROM skill_binding_meta WHERE skill_id IN ({placeholders})",
                ids,
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
        finally:
            conn.close()
        out: dict[str, dict[str, Any]] = {}
        for row in rows:
            try:
                safety = json.loads(row["safety_json"] or "{}")
            except json.JSONDecodeError:
                safety = {}
            out[row["skill_id"]] = {"tier": row["tier"], "safety": safety if isinstance(safety, dict) else {}}
        return out

    def tools_for_skills(self, skill_ids: Sequence[str]) -> dict[str, list[str]]:
        """Skills with a meta row map to their tool list (possibly empty). Unknown skills are omitted."""
        ids = [str(item).strip() for item in skill_ids if str(item).strip()]
        if not ids:
            return {}
        conn = self._connect()
        if conn is None:
            return {}
        try:
            _ensure_schema(conn)
            placeholders = ",".join("?" for _ in ids)
            meta_rows = conn.execute(
                f"SELECT skill_id FROM skill_binding_meta WHERE skill_id IN ({placeholders})",
                ids,
            ).fetchall()
            present = [row["skill_id"] for row in meta_rows]
            if not present:
                return {}
            tool_rows = conn.execute(
                f"""
                SELECT skill_id, tool_id
                FROM skill_tool_bindings
                WHERE skill_id IN ({placeholders})
                ORDER BY position ASC, tool_id ASC
                """,
                ids,
            ).fetchall()
        except sqlite3.OperationalError:
            return {}
        finally:
            conn.close()
        out = {sid: [] for sid in present}
        for row in tool_rows:
            bucket = out.get(row["skill_id"])
            if bucket is not None and row["tool_id"] not in bucket:
                bucket.append(row["tool_id"])
        return out


def sqlite_tools_for_skills(skill_ids: Iterable[str], db_path: Optional[str] = None) -> dict[str, list[str]]:
    """Read binding rows for turn-time tool scoping. Fail closed to {} when the DB is unavailable."""
    try:
        return SkillToolBindingRepository(db_path=db_path).tools_for_skills(list(skill_ids))
    except Exception:
        return {}
