"""
Remote Host SQLite Repository Mixin [CARD-160].
"""

from datetime import datetime, timezone
from typing import List, Optional

from src.domain.remote.models import RemoteHost


class RemoteHostRepositoryMixin:
    """Methods for persisting and managing remote host connection profiles."""

    def _init_remote_hosts_table(self, conn) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS remote_hosts (
                id TEXT PRIMARY KEY,
                label TEXT NOT NULL,
                host TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 22,
                username TEXT NOT NULL,
                auth_type TEXT NOT NULL DEFAULT 'password',
                credential_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_remote_hosts_label ON remote_hosts(label);")

    def save_remote_host(self, host: RemoteHost) -> bool:
        """Create or update a remote host profile."""
        now_str = datetime.now(timezone.utc).isoformat()
        created_at = host.created_at or now_str
        updated_at = now_str

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO remote_hosts (id, label, host, port, username, auth_type, credential_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    label = excluded.label,
                    host = excluded.host,
                    port = excluded.port,
                    username = excluded.username,
                    auth_type = excluded.auth_type,
                    credential_id = excluded.credential_id,
                    updated_at = excluded.updated_at
                """,
                (
                    host.id,
                    host.label,
                    host.host,
                    host.port,
                    host.username,
                    host.auth_type,
                    host.credential_id,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
            return True
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def get_remote_host(self, host_id: str) -> Optional[RemoteHost]:
        """Fetch a remote host profile by id."""
        if not host_id:
            return None
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, label, host, port, username, auth_type, credential_id, created_at, updated_at
                FROM remote_hosts
                WHERE id = ?
                """,
                (host_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return RemoteHost(
                id=row[0],
                label=row[1],
                host=row[2],
                port=row[3],
                username=row[4],
                auth_type=row[5],
                credential_id=row[6],
                created_at=row[7],
                updated_at=row[8],
            )
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def list_remote_hosts(self) -> List[RemoteHost]:
        """List all configured remote host profiles ordered by label."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, label, host, port, username, auth_type, credential_id, created_at, updated_at
                FROM remote_hosts
                ORDER BY label ASC, id ASC
                """
            )
            rows = cur.fetchall()
            return [
                RemoteHost(
                    id=row[0],
                    label=row[1],
                    host=row[2],
                    port=row[3],
                    username=row[4],
                    auth_type=row[5],
                    credential_id=row[6],
                    created_at=row[7],
                    updated_at=row[8],
                )
                for row in rows
            ]
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()

    def delete_remote_host(self, host_id: str) -> bool:
        """Delete a remote host profile by id."""
        if not host_id:
            return False
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM remote_hosts WHERE id = ?", (host_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            return deleted
        finally:
            if getattr(self, "_mem_conn", None) is None:
                conn.close()
