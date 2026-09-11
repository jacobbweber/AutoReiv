"""
Capability catalog SQLite repository [CARD-217 / REQ-CAPCAT-005].
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Callable, List, Optional, Sequence

from src.domain.capabilities.models import CapabilityIndexEntry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapabilityCatalogRepository:
    """Durable capability_index persistence."""

    def __init__(
        self,
        connection_manager: Any = None,
        connection_factory: Optional[Callable[[], Any]] = None,
    ):
        self._cm = connection_manager
        self._connection_factory = connection_factory

    def _get_connection(self):
        if self._connection_factory:
            return self._connection_factory()
        if self._cm and hasattr(self._cm, "_get_connection"):
            return self._cm._get_connection()
        raise ValueError("CapabilityCatalogRepository requires connection_manager or connection_factory.")

    @property
    def _mem_conn(self):
        return getattr(self._cm, "_mem_conn", None)

    def _close_if_needed(self, conn) -> None:
        if not self._connection_factory and self._mem_conn is None and hasattr(conn, "close"):
            conn.close()

    @staticmethod
    def _row_to_entry(row: Any) -> CapabilityIndexEntry:
        return CapabilityIndexEntry(
            id=row["id"],
            kind=row["kind"],
            name=row["name"],
            summary=row["summary"] or "",
            keywords=json.loads(row["keywords_json"] or "[]"),
            roles=json.loads(row["roles_json"] or "[]"),
            trust_tier=row["trust_tier"],
            risk_level=row["risk_level"],
            requires_hitl=bool(row["requires_hitl"]),
            source=row["source"] or "self_authored",
            metadata=json.loads(row["metadata_json"] or "{}"),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def upsert_entry(self, entry: CapabilityIndexEntry) -> CapabilityIndexEntry:
        now = _now()
        payload = entry.model_copy(update={"updated_at": now})
        if not payload.created_at:
            payload = payload.model_copy(update={"created_at": now})
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO capability_index (
                    id, kind, name, summary, keywords_json, roles_json,
                    trust_tier, risk_level, requires_hitl, source, metadata_json,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    name=excluded.name,
                    summary=excluded.summary,
                    keywords_json=excluded.keywords_json,
                    roles_json=excluded.roles_json,
                    trust_tier=excluded.trust_tier,
                    risk_level=excluded.risk_level,
                    requires_hitl=excluded.requires_hitl,
                    source=excluded.source,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    payload.id,
                    payload.kind.value if hasattr(payload.kind, "value") else str(payload.kind),
                    payload.name,
                    payload.summary,
                    json.dumps(list(payload.keywords)),
                    json.dumps(list(payload.roles)),
                    payload.trust_tier.value if hasattr(payload.trust_tier, "value") else str(payload.trust_tier),
                    payload.risk_level.value if hasattr(payload.risk_level, "value") else str(payload.risk_level),
                    1 if payload.requires_hitl else 0,
                    payload.source,
                    json.dumps(dict(payload.metadata or {})),
                    payload.created_at or now,
                    payload.updated_at,
                ),
            )
            conn.commit()
            return payload
        finally:
            self._close_if_needed(conn)

    def get_entry(self, entry_id: str) -> Optional[CapabilityIndexEntry]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM capability_index WHERE id = ?", (entry_id,))
            row = cur.fetchone()
            return self._row_to_entry(row) if row else None
        finally:
            self._close_if_needed(conn)

    def list_entries(
        self,
        *,
        kinds: Optional[Sequence[str]] = None,
        trust_tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CapabilityIndexEntry]:
        lim = max(1, min(int(limit or 50), 256))
        off = max(0, int(offset or 0))
        clauses: List[str] = []
        params: List[Any] = []
        if kinds:
            placeholders = ",".join("?" for _ in kinds)
            clauses.append(f"kind IN ({placeholders})")
            params.extend([str(k).lower() for k in kinds])
        if trust_tier:
            clauses.append("trust_tier = ?")
            params.append(str(trust_tier).lower())
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM capability_index{where} ORDER BY name COLLATE NOCASE, id LIMIT ? OFFSET ?"
        params.extend([lim, off])
        conn = self._get_connection()
        try:
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_entry(r) for r in rows]
        finally:
            self._close_if_needed(conn)

    def count_entries(self) -> int:
        conn = self._get_connection()
        try:
            row = conn.execute("SELECT COUNT(*) AS c FROM capability_index").fetchone()
            return int(row["c"] if row and "c" in row.keys() else (row[0] if row else 0))
        finally:
            self._close_if_needed(conn)
