"""
Self-Scaffold Spine [CARD-218 / REQ-SCAFFOLD-001..006].

draft → sandbox_exec → version → HITL approve → trusted.
Candidate cannot run unsandboxed. Unscoped trusted write = reject.
Rollback restores prior trusted via UserSkillCatalog snapshots.
Cite: SoK Agentic Skills arXiv 2602.20867.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from src.domain.capabilities.models import (
    CapabilityIndexEntry,
    CapabilityKind,
    TrustTier,
)
from src.domain.capabilities.scaffold import ScaffoldPhase, ScaffoldRecord, utc_now_iso


class CandidateUnsandboxedError(PermissionError):
    """Candidate skill/tool cannot run outside sandbox [REQ-SCAFFOLD-003]."""


class UnscopedTrustedWriteError(PermissionError):
    """Direct write/promote to trusted without spine path [REQ-SCAFFOLD-005]."""


def _new_id() -> str:
    return f"scf_{uuid.uuid4().hex[:12]}"


def _cap_id(kind: CapabilityKind | str, pack_id: str) -> str:
    k = kind.value if isinstance(kind, CapabilityKind) else str(kind).strip().lower()
    return f"{k}.{pack_id}"


class SelfScaffoldSpine:
    """Standing self-scaffold write spine over catalog + UserSkillCatalog."""

    def __init__(
        self,
        *,
        spine_repo: Any,
        capability_repo: Any,
        catalog: Any,
    ) -> None:
        self.spine_repo = spine_repo
        self.capability_repo = capability_repo
        self.catalog = catalog

    def get(self, record_id: str) -> ScaffoldRecord:
        rec = self.spine_repo.get(record_id)
        if rec is None:
            raise KeyError(f"scaffold record not found: {record_id}")
        return rec

    def list_candidates(self, *, limit: int = 50) -> List[ScaffoldRecord]:
        """Forge candidate queue: non-trusted / not fully promoted rows."""
        return self.spine_repo.list_candidates(limit=limit)

    def draft(
        self,
        *,
        kind: CapabilityKind | str,
        name: str,
        pack_id: str,
        summary: str = "",
        content: str = "",
        proposal_id: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        skip_disk_write: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScaffoldRecord:
        """Always land as candidate — never trusted by default [REQ-SCAFFOLD-001]."""
        kind_e = CapabilityKind(str(kind.value if isinstance(kind, CapabilityKind) else kind).strip().lower())
        pid = (pack_id or "").strip()
        if not pid:
            raise ValueError("pack_id is required.")
        nm = (name or "").strip()
        if not nm:
            raise ValueError("name is required.")

        # Capture prior trusted snapshot id if a trusted pack already exists.
        prior_snap: Optional[str] = None
        existing_pack = None
        try:
            existing_pack = self.catalog.read_pack(pid)
        except Exception:
            existing_pack = None
        if existing_pack and existing_pack.get("success"):
            snap = self.catalog.snapshot_pack(pid)
            if snap.get("success"):
                prior_snap = snap.get("snapshot_id")

        if not skip_disk_write:
            saved = self.catalog.save_pack(
                pid,
                nm,
                summary or nm,
                content or f"# {nm}\n",
            )
            if not saved.get("success"):
                raise ValueError(saved.get("error") or "UserSkillCatalog.save_pack failed.")

        cap_id = _cap_id(kind_e, pid)
        entry = CapabilityIndexEntry.self_authored(
            id=cap_id,
            kind=kind_e,
            name=nm,
            summary=summary or "",
            keywords=list(keywords or [nm, pid, "scaffold", "candidate"]),
            metadata={"scaffold": True, "pack_id": pid},
        )
        self.capability_repo.upsert_entry(entry)

        rec = ScaffoldRecord(
            id=_new_id(),
            kind=kind_e,
            name=nm,
            summary=summary or "",
            pack_id=pid,
            capability_id=cap_id,
            phase=ScaffoldPhase.DRAFT,
            trust_tier=TrustTier.CANDIDATE,
            sandboxed=False,
            prior_trusted_snapshot_id=prior_snap,
            proposal_id=(proposal_id or "").strip() or None,
            content=content or "",
            metadata=dict(metadata or {}),
        )
        return self.spine_repo.upsert(rec)

    def mark_sandbox_exec(self, record_id: str, *, evidence: str = "") -> ScaffoldRecord:
        rec = self.get(record_id)
        if rec.phase == ScaffoldPhase.TRUSTED and not rec.rolled_back:
            # Already trusted; keep sandboxed true for honesty.
            return rec
        now = utc_now_iso()
        updated = rec.model_copy(
            update={
                "phase": ScaffoldPhase.SANDBOX_EXEC,
                "sandboxed": True,
                "sandbox_evidence": (evidence or "").strip() or "sandbox_ok",
                "updated_at": now,
            }
        )
        return self.spine_repo.upsert(updated)

    def assert_can_run(self, record_id: str) -> Dict[str, Any]:
        """Fail closed if candidate and not sandboxed [REQ-SCAFFOLD-003]."""
        rec = self.get(record_id)
        if rec.trust_tier == TrustTier.TRUSTED and rec.phase == ScaffoldPhase.TRUSTED:
            return {"ok": True, "record_id": rec.id, "trust_tier": rec.trust_tier.value}
        if not rec.sandboxed or rec.phase == ScaffoldPhase.DRAFT:
            raise CandidateUnsandboxedError(
                "candidate cannot run unsandboxed; complete sandbox_exec first"
            )
        return {
            "ok": True,
            "record_id": rec.id,
            "trust_tier": rec.trust_tier.value,
            "sandboxed": True,
            "phase": rec.phase.value,
        }

    def version(self, record_id: str) -> ScaffoldRecord:
        rec = self.get(record_id)
        if not rec.sandboxed:
            raise CandidateUnsandboxedError(
                "candidate cannot run unsandboxed; sandbox_exec required before version"
            )
        snap = self.catalog.snapshot_pack(rec.pack_id)
        if not snap.get("success"):
            # Pack may be brand-new; create a version marker anyway.
            snap_id = f"ver_{uuid.uuid4().hex[:10]}"
        else:
            snap_id = snap.get("snapshot_id") or f"ver_{uuid.uuid4().hex[:10]}"
        updated = rec.model_copy(
            update={
                "phase": ScaffoldPhase.VERSIONED,
                "snapshot_id": snap_id,
                "updated_at": utc_now_iso(),
            }
        )
        return self.spine_repo.upsert(updated)

    def hitl_approve(self, record_id: str) -> ScaffoldRecord:
        """HITL approve → trusted. Requires sandbox + version [REQ-SCAFFOLD-002]."""
        rec = self.get(record_id)
        if not rec.sandboxed:
            raise CandidateUnsandboxedError(
                "candidate cannot run unsandboxed; sandbox_exec required before approve"
            )
        if rec.phase not in {
            ScaffoldPhase.VERSIONED,
            ScaffoldPhase.SANDBOX_EXEC,
            ScaffoldPhase.HITL_APPROVED,
        }:
            if rec.phase == ScaffoldPhase.DRAFT:
                raise CandidateUnsandboxedError(
                    "candidate cannot run unsandboxed; complete sandbox and version first"
                )
        # Ensure a version snapshot exists.
        if not rec.snapshot_id:
            rec = self.version(rec.id)

        entry = self.capability_repo.get_entry(rec.capability_id)
        if entry is not None:
            promoted = entry.model_copy(
                update={
                    "trust_tier": TrustTier.TRUSTED,
                    "updated_at": utc_now_iso(),
                }
            )
            self.capability_repo.upsert_entry(promoted)

        updated = rec.model_copy(
            update={
                "phase": ScaffoldPhase.TRUSTED,
                "trust_tier": TrustTier.TRUSTED,
                "rolled_back": False,
                "updated_at": utc_now_iso(),
            }
        )
        return self.spine_repo.upsert(updated)

    def rollback(self, record_id: str) -> Dict[str, Any]:
        """Restore prior trusted snapshot [REQ-SCAFFOLD-004]."""
        rec = self.get(record_id)
        prior = rec.prior_trusted_snapshot_id
        if not prior:
            return {
                "success": False,
                "error": "No prior trusted snapshot to restore.",
                "record_id": rec.id,
            }
        restored = self.catalog.rollback_pack(rec.pack_id, snapshot_id=prior)
        if not restored.get("success"):
            return {
                "success": False,
                "error": restored.get("error") or "rollback_pack failed",
                "record_id": rec.id,
            }
        entry = self.capability_repo.get_entry(rec.capability_id)
        if entry is not None:
            self.capability_repo.upsert_entry(
                entry.model_copy(
                    update={
                        "trust_tier": TrustTier.TRUSTED,
                        "updated_at": utc_now_iso(),
                    }
                )
            )
        updated = rec.model_copy(
            update={
                "phase": ScaffoldPhase.TRUSTED,
                "trust_tier": TrustTier.TRUSTED,
                "rolled_back": True,
                "snapshot_id": prior,
                "updated_at": utc_now_iso(),
                "metadata": {
                    **dict(rec.metadata or {}),
                    "rollback_restored_snapshot_id": prior,
                },
            }
        )
        self.spine_repo.upsert(updated)
        return {
            "success": True,
            "record_id": rec.id,
            "prior_trusted_snapshot_id": prior,
            "pack_id": rec.pack_id,
            "restored": restored,
        }

    def write_trusted_unscoped(self, **_kwargs: Any) -> None:
        """Explicit reject path for unscoped trusted writes [REQ-SCAFFOLD-005]."""
        raise UnscopedTrustedWriteError(
            "unscoped write to trusted rejected; use draft→sandbox→version→HITL spine"
        )
