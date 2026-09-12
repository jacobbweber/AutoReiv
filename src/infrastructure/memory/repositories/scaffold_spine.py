"""Durable scaffold_spine repository [CARD-218 / REQ-SCAFFOLD-002]."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, List, Optional

from src.domain.capabilities.scaffold import ScaffoldRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScaffoldSpineRepository:
    def __init__(self, connection_manager: Any = None, connection_factory: Any = None):
        self._cm = connection_manager
        self._connection_factory = connection_factory

    def _get_connection(self):
        if self._connection_factory is not None:
            return self._connection_factory()
        if self._cm is not None:
            getter = getattr(self._cm, "_get_connection", None) or getattr(
                self._cm, "get_connection", None
            )
            if callable(getter):
                return getter()
            if hasattr(self._cm, "connection"):
                return self._cm.connection
        raise ValueError("ScaffoldSpineRepository requires connection_manager or connection_factory.")

    @property
    def _mem_conn(self):
        return getattr(self._cm, "_mem_conn", None)

    def _close_if_needed(self, conn) -> None:
        if not self._connection_factory and self._mem_conn is None and hasattr(conn, "close"):
            conn.close()

    @staticmethod
    def _row_to_record(row: Any) -> ScaffoldRecord:
        return ScaffoldRecord(
            id=row["id"],
            kind=row["kind"],
            name=row["name"],
            summary=row["summary"] or "",
            pack_id=row["pack_id"],
            capability_id=row["capability_id"],
            phase=row["phase"],
            trust_tier=row["trust_tier"],
            sandboxed=bool(row["sandboxed"]),
            sandbox_evidence=row["sandbox_evidence"] or "",
            snapshot_id=row["snapshot_id"],
            prior_trusted_snapshot_id=row["prior_trusted_snapshot_id"],
            proposal_id=row["proposal_id"],
            content=row["content"] or "",
            rolled_back=bool(row["rolled_back"]),
            metadata=json.loads(row["metadata_json"] or "{}"),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )

    def upsert(self, record: ScaffoldRecord) -> ScaffoldRecord:
        now = _now()
        payload = record.model_copy(update={"updated_at": now})
        if not payload.created_at:
            payload = payload.model_copy(update={"created_at": now})
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO scaffold_spine (
                    id, kind, name, summary, pack_id, capability_id,
                    phase, trust_tier, sandboxed, sandbox_evidence,
                    snapshot_id, prior_trusted_snapshot_id, proposal_id,
                    content, rolled_back, metadata_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    kind=excluded.kind,
                    name=excluded.name,
                    summary=excluded.summary,
                    pack_id=excluded.pack_id,
                    capability_id=excluded.capability_id,
                    phase=excluded.phase,
                    trust_tier=excluded.trust_tier,
                    sandboxed=excluded.sandboxed,
                    sandbox_evidence=excluded.sandbox_evidence,
                    snapshot_id=excluded.snapshot_id,
                    prior_trusted_snapshot_id=excluded.prior_trusted_snapshot_id,
                    proposal_id=excluded.proposal_id,
                    content=excluded.content,
                    rolled_back=excluded.rolled_back,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (
                    payload.id,
                    payload.kind.value if hasattr(payload.kind, "value") else str(payload.kind),
                    payload.name,
                    payload.summary,
                    payload.pack_id,
                    payload.capability_id,
                    payload.phase.value if hasattr(payload.phase, "value") else str(payload.phase),
                    payload.trust_tier.value
                    if hasattr(payload.trust_tier, "value")
                    else str(payload.trust_tier),
                    1 if payload.sandboxed else 0,
                    payload.sandbox_evidence or "",
                    payload.snapshot_id,
                    payload.prior_trusted_snapshot_id,
                    payload.proposal_id,
                    payload.content or "",
                    1 if payload.rolled_back else 0,
                    json.dumps(dict(payload.metadata or {})),
                    payload.created_at or now,
                    payload.updated_at,
                ),
            )
            conn.commit()
            return payload
        finally:
            self._close_if_needed(conn)

    def get(self, record_id: str) -> Optional[ScaffoldRecord]:
        conn = self._get_connection()
        try:
            cur = conn.execute("SELECT * FROM scaffold_spine WHERE id = ?", (record_id,))
            row = cur.fetchone()
            return self._row_to_record(row) if row else None
        finally:
            self._close_if_needed(conn)

    def list_candidates(self, *, limit: int = 50) -> List[ScaffoldRecord]:
        """Forge queue: candidates not yet trusted (or still in-flight)."""
        lim = max(1, min(int(limit or 50), 200))
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM scaffold_spine
                WHERE trust_tier = 'candidate'
                   OR phase IN ('draft', 'sandbox_exec', 'versioned', 'hitl_approved')
                ORDER BY updated_at DESC
                LIMIT ?
                """,
                (lim,),
            ).fetchall()
            return [self._row_to_record(r) for r in rows]
        finally:
            self._close_if_needed(conn)
