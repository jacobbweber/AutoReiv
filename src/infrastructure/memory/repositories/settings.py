"""
Settings key-value repository mixin [REQ-SET-001].

CARD-570: agent and skill definitions are files (platform/ + data dir), not DB rows.
"""

import json
from datetime import datetime, timezone
from typing import Any


class SettingsRepositoryMixin:
    """Methods for persisting JSON key-value configurations."""

    def set_setting(self, key: str, value: Any) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        val_json = json.dumps(value)
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json = excluded.value_json,
                    updated_at = excluded.updated_at
                """,
                (key, val_json, now_str),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

    def get_setting(self, key: str, default: Any = None) -> Any:
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("SELECT value_json FROM settings WHERE key = ?", (key,))
            r = cur.fetchone()
            if not r or not r["value_json"]:
                return default
            return json.loads(r["value_json"])
        finally:
            if self._mem_conn is None:
                conn.close()
