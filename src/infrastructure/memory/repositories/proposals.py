"""
Follow-up job proposals repository mixin [REQ-ORCH-043].
SQLite-backed. Drafts are not jobs that auto-run.
"""

from datetime import datetime, timezone
from typing import Any, List

from src.domain.orchestration.errors import InvalidProposalStatusError, ProposalNotFoundError
from src.domain.orchestration.models import Proposal, ProposalKind, ProposalStatus

_PROPOSAL_KINDS = {item.value for item in ProposalKind}
_PROPOSAL_STATUSES = {item.value for item in ProposalStatus}

_PROPOSAL_COLUMNS = "id, kind, payload_json, status, requested_by_job_id, created_at, updated_at"


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    text = str(value)
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _require_kind(kind: Any) -> str:
    raw = kind.value if isinstance(kind, ProposalKind) else str(kind)
    if raw not in _PROPOSAL_KINDS:
        raise InvalidProposalStatusError(
            f"Invalid proposal kind {raw!r}. Allowed: skill|tool|workflow|followup_job|agent."
        )
    return raw


def _require_status(status: Any) -> str:
    raw = status.value if isinstance(status, ProposalStatus) else str(status)
    if raw not in _PROPOSAL_STATUSES:
        raise InvalidProposalStatusError(
            f"Invalid proposal status {raw!r}. Allowed: draft|approved|rejected."
        )
    return raw


class ProposalRepositoryMixin:
    """CRUD for durable proposal rows (followup_job now; other kinds later)."""

    def _proposal_from_row(self, row: Any) -> Proposal:
        return Proposal(
            id=row["id"],
            kind=row["kind"],
            payload_json=row["payload_json"],
            status=row["status"],
            requested_by_job_id=row["requested_by_job_id"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    def create_proposal(self, proposal: Proposal) -> Proposal:
        kind = _require_kind(proposal.kind)
        status = _require_status(proposal.status)
        now = _utc_iso()
        created_at = proposal.created_at.isoformat() if isinstance(proposal.created_at, datetime) else now
        updated_at = proposal.updated_at.isoformat() if isinstance(proposal.updated_at, datetime) else now
        conn = self._get_connection()
        try:
            conn.execute(
                f"""
                INSERT INTO proposals ({_PROPOSAL_COLUMNS})
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    proposal.id,
                    kind,
                    proposal.payload_json,
                    status,
                    proposal.requested_by_job_id,
                    created_at,
                    updated_at,
                ),
            )
            conn.commit()
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_proposal(proposal.id)

    def get_proposal(self, proposal_id: str) -> Proposal:
        conn = self._get_connection()
        try:
            row = conn.execute(
                f"SELECT {_PROPOSAL_COLUMNS} FROM proposals WHERE id = ?",
                (proposal_id,),
            ).fetchone()
            if row is None:
                raise ProposalNotFoundError(f"Proposal {proposal_id} not found.")
            return self._proposal_from_row(row)
        finally:
            if self._mem_conn is None:
                conn.close()

    def list_proposals_for_job(self, requested_by_job_id: str) -> List[Proposal]:
        conn = self._get_connection()
        try:
            rows = conn.execute(
                f"""
                SELECT {_PROPOSAL_COLUMNS} FROM proposals
                WHERE requested_by_job_id = ?
                ORDER BY created_at DESC
                """,
                (requested_by_job_id,),
            ).fetchall()
            return [self._proposal_from_row(row) for row in rows]
        finally:
            if self._mem_conn is None:
                conn.close()

    def update_proposal_status(self, proposal_id: str, status: str) -> Proposal:
        status_value = _require_status(status)
        now = _utc_iso()
        conn = self._get_connection()
        try:
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE proposals
                SET status = ?, updated_at = ?
                WHERE id = ?
                """,
                (status_value, now, proposal_id),
            )
            conn.commit()
            if cur.rowcount == 0:
                raise ProposalNotFoundError(f"Proposal {proposal_id} not found.")
        finally:
            if self._mem_conn is None:
                conn.close()
        return self.get_proposal(proposal_id)
