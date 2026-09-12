"""
Capability catalog index models [CARD-217 / REQ-CAPCAT-001..002].

Progressive match-only load over primitives. Trust tiers start at candidate
for self-authored entries. Fail closed on unknown kinds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CapabilityKind(str, Enum):
    AGENT = "agent"
    SKILL = "skill"
    TOOL = "tool"
    PACK = "pack"
    ROUTINE = "routine"


class TrustTier(str, Enum):
    CANDIDATE = "candidate"
    REVIEWED = "reviewed"
    TRUSTED = "trusted"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


_ALLOWED_KINDS = {k.value for k in CapabilityKind}


class CapabilityIndexEntry(BaseModel):
    """Durable capability index row for match-only resolve."""

    id: str = Field(..., min_length=1)
    kind: CapabilityKind
    name: str = Field(..., min_length=1)
    summary: str = ""
    keywords: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)
    trust_tier: TrustTier = TrustTier.CANDIDATE
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_hitl: bool = False
    source: str = "self_authored"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)

    @field_validator("kind", mode="before")
    @classmethod
    def _fail_closed_unknown_kind(cls, value: Any) -> Any:
        if isinstance(value, CapabilityKind):
            return value
        raw = str(value or "").strip().lower()
        if raw not in _ALLOWED_KINDS:
            raise ValueError(f"unknown capability kind (fail closed): {value!r}")
        return raw

    @classmethod
    def self_authored(
        cls,
        *,
        id: str,
        kind: CapabilityKind | str,
        name: str,
        summary: str = "",
        keywords: Optional[List[str]] = None,
        roles: Optional[List[str]] = None,
        risk_level: RiskLevel | str = RiskLevel.MEDIUM,
        requires_hitl: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> "CapabilityIndexEntry":
        """Factory: self-authored entries always start as candidate [REQ-CAPCAT-002]."""
        return cls(
            id=id,
            kind=kind,
            name=name,
            summary=summary,
            keywords=list(keywords or []),
            roles=list(roles or []),
            trust_tier=TrustTier.CANDIDATE,
            risk_level=risk_level,
            requires_hitl=requires_hitl,
            source="self_authored",
            metadata=dict(metadata or {}),
        )
