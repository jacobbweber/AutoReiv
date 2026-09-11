"""Self-scaffold spine domain models [CARD-218 / REQ-SCAFFOLD-001..005].

Lifecycle: draft → sandbox_exec → versioned → hitl_approved → trusted.
Cite: SoK Agentic Skills arXiv 2602.20867.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from src.domain.capabilities.models import CapabilityKind, TrustTier


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ScaffoldPhase(str, Enum):
    DRAFT = "draft"
    SANDBOX_EXEC = "sandbox_exec"
    VERSIONED = "versioned"
    HITL_APPROVED = "hitl_approved"
    TRUSTED = "trusted"


class ScaffoldRecord(BaseModel):
    """Durable self-scaffold spine row."""

    id: str = Field(..., min_length=1)
    kind: CapabilityKind
    name: str = Field(..., min_length=1)
    summary: str = ""
    pack_id: str = Field(..., min_length=1)
    capability_id: str = Field(..., min_length=1)
    phase: ScaffoldPhase = ScaffoldPhase.DRAFT
    trust_tier: TrustTier = TrustTier.CANDIDATE
    sandboxed: bool = False
    sandbox_evidence: str = ""
    snapshot_id: Optional[str] = None
    prior_trusted_snapshot_id: Optional[str] = None
    proposal_id: Optional[str] = None
    content: str = ""
    rolled_back: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
