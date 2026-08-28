"""
Session Artifact Repository Mixin [REQ-ART-001, REQ-ART-002].
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from src.domain.memory.models import SessionArtifact


class ArtifactRepositoryMixin:
    """Methods for managing ephemeral and pinned session artifacts."""

    def save_artifact(self, artifact: SessionArtifact) -> SessionArtifact:
        """Persist or update an artifact linked to a session."""
        now = datetime.now(timezone.utc)
        expires_at = artifact.expires_at or (now + timedelta(days=7))
        art_id = artifact.id or f"art_{uuid.uuid4().hex[:12]}"

        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO session_artifacts (
                    id, session_id, title, content_type, content, summary, item_count, is_pinned, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    art_id,
                    artifact.session_id,
                    artifact.title,
                    artifact.content_type,
                    artifact.content,
                    artifact.summary,
                    artifact.item_count,
                    1 if artifact.is_pinned else 0,
                    expires_at.isoformat(),
                    (artifact.created_at or now).isoformat(),
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()

        return SessionArtifact(
            id=art_id,
            session_id=artifact.session_id,
            title=artifact.title,
            content_type=artifact.content_type,
            content=artifact.content,
            summary=artifact.summary,
            item_count=artifact.item_count,
            is_pinned=artifact.is_pinned,
            expires_at=expires_at,
            created_at=artifact.created_at or now,
        )

    def get_artifact(self, artifact_id: str) -> Optional[SessionArtifact]:
        """Fetch an artifact by its ID."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, session_id, title, content_type, content, summary, item_count, is_pinned, expires_at, created_at
                FROM session_artifacts WHERE id = ?
                """,
                (artifact_id,),
            )
            row = cur.fetchone()
            if not row:
                return None

            expires_at = None
            if row["expires_at"]:
                try:
                    expires_at = datetime.fromisoformat(row["expires_at"])
                except Exception:
                    pass

            created_at = datetime.now(timezone.utc)
            if row["created_at"]:
                try:
                    created_at = datetime.fromisoformat(row["created_at"])
                except Exception:
                    pass

            return SessionArtifact(
                id=row["id"],
                session_id=row["session_id"],
                title=row["title"],
                content_type=row["content_type"],
                content=row["content"],
                summary=row["summary"],
                item_count=row["item_count"] or 0,
                is_pinned=bool(row["is_pinned"]),
                expires_at=expires_at,
                created_at=created_at,
            )
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_session_artifacts(self, session_id: str) -> List[SessionArtifact]:
        """List all artifacts attached to a given session."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, session_id, title, content_type, content, summary, item_count, is_pinned, expires_at, created_at
                FROM session_artifacts WHERE session_id = ?
                ORDER BY created_at DESC
                """,
                (session_id,),
            )
            rows = cur.fetchall()
            artifacts = []
            for row in rows:
                expires_at = None
                if row["expires_at"]:
                    try:
                        expires_at = datetime.fromisoformat(row["expires_at"])
                    except Exception:
                        pass

                created_at = datetime.now(timezone.utc)
                if row["created_at"]:
                    try:
                        created_at = datetime.fromisoformat(row["created_at"])
                    except Exception:
                        pass

                artifacts.append(
                    SessionArtifact(
                        id=row["id"],
                        session_id=row["session_id"],
                        title=row["title"],
                        content_type=row["content_type"],
                        content=row["content"],
                        summary=row["summary"],
                        item_count=row["item_count"] or 0,
                        is_pinned=bool(row["is_pinned"]),
                        expires_at=expires_at,
                        created_at=created_at,
                    )
                )
            return artifacts
        finally:
            if self._mem_conn is None:
                conn.close()

    def pin_artifact(self, artifact_id: str, is_pinned: bool = True) -> bool:
        """Toggle pinned status for an artifact."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "UPDATE session_artifacts SET is_pinned = ? WHERE id = ?",
                (1 if is_pinned else 0, artifact_id),
            )
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def delete_artifact(self, artifact_id: str) -> bool:
        """Delete an artifact by ID."""
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute("DELETE FROM session_artifacts WHERE id = ?", (artifact_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            if self._mem_conn is None:
                conn.close()

    def prune_expired_artifacts(self) -> int:
        """Purge all unpinned artifacts whose expiration timestamp has passed."""
        now = datetime.now(timezone.utc).isoformat()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                "DELETE FROM session_artifacts WHERE is_pinned = 0 AND expires_at < ?",
                (now,),
            )
            conn.commit()
            return cur.rowcount
        finally:
            if self._mem_conn is None:
                conn.close()
