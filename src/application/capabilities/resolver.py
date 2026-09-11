"""
Match-only capability catalog resolver [CARD-217 / REQ-CAPCAT-003..004].

Returns a matched subset for intent/role/keyword. Never dumps the full catalog
into a prompt payload. Operator registry listing is separate and capped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, Sequence

from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind


class CapabilityCatalogStore(Protocol):
    def upsert_entry(self, entry: CapabilityIndexEntry) -> CapabilityIndexEntry: ...

    def get_entry(self, entry_id: str) -> Optional[CapabilityIndexEntry]: ...

    def list_entries(
        self,
        *,
        kinds: Optional[Sequence[str]] = None,
        trust_tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CapabilityIndexEntry]: ...

    def count_entries(self) -> int: ...


_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "") if t]


@dataclass(frozen=True)
class ResolveResult:
    matched: tuple[CapabilityIndexEntry, ...]
    query: str
    role: Optional[str] = None
    total_indexed: int = 0
    miss: bool = False
    facts: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        from src.application.capabilities.progressive_skills import entry_to_resolve_view

        return {
            "matched": [entry_to_resolve_view(e) for e in self.matched],
            "count": len(self.matched),
            "query": self.query,
            "role": self.role,
            "total_indexed": self.total_indexed,
            "miss": self.miss,
            "facts": list(self.facts),
            # Explicit: this payload is a subset, never a full dump.
            "subset_only": True,
            # CARD-228: skill rows are metadata-only; bodies load on phase bind.
            "skill_bodies_omitted": True,
            "progressive_skill_disclosure": True,
        }


class CapabilityCatalogResolver:
    """Progressive match-only load. No dump-all / list-all-for-prompt method."""

    DEFAULT_LIMIT = 12
    MAX_LIMIT = 32
    OPERATOR_MAX_LIMIT = 100

    def __init__(self, store: CapabilityCatalogStore):
        self._store = store

    def upsert(self, entry: CapabilityIndexEntry) -> CapabilityIndexEntry:
        return self._store.upsert_entry(entry)

    def resolve(
        self,
        intent: str,
        *,
        role: Optional[str] = None,
        kinds: Optional[Sequence[str]] = None,
        limit: int = DEFAULT_LIMIT,
    ) -> ResolveResult:
        """Match intent/role/keywords to a subset. Empty intent -> miss, not dump-all."""
        query = (intent or "").strip()
        total = self._store.count_entries()
        lim = max(1, min(int(limit or self.DEFAULT_LIMIT), self.MAX_LIMIT))

        if not query and not (role or "").strip():
            return ResolveResult(
                matched=(),
                query=query,
                role=role,
                total_indexed=total,
                miss=True,
                facts=("capability_resolve: miss (empty intent/role; fail closed, no dump-all)",),
            )

        kind_filter: Optional[List[str]] = None
        if kinds:
            kind_filter = []
            for k in kinds:
                raw = str(k or "").strip().lower()
                try:
                    kind_filter.append(CapabilityKind(raw).value)
                except ValueError as exc:
                    raise ValueError(f"unknown capability kind (fail closed): {k!r}") from exc

        # Pull a bounded working set for matching (not unbounded dump into prompt).
        # Cap scan window well above match limit but far below "dump everything".
        scan_limit = min(max(lim * 8, 64), 256)
        candidates = self._store.list_entries(kinds=kind_filter, limit=scan_limit, offset=0)
        tokens = set(_tokenize(query))
        role_norm = (role or "").strip().lower() or None

        scored: List[tuple[int, CapabilityIndexEntry]] = []
        for entry in candidates:
            score = 0
            kw = {str(x).lower() for x in (entry.keywords or [])}
            roles = {str(x).lower() for x in (entry.roles or [])}
            name_tokens = set(_tokenize(entry.name))
            summary_tokens = set(_tokenize(entry.summary))
            if tokens:
                score += 3 * len(tokens & kw)
                score += 2 * len(tokens & name_tokens)
                score += len(tokens & summary_tokens)
            if role_norm and role_norm in roles:
                score += 4
            if score > 0:
                scored.append((score, entry))

        scored.sort(key=lambda pair: (-pair[0], pair[1].name.lower(), pair[1].id))
        matched = tuple(entry for _, entry in scored[:lim])
        miss = len(matched) == 0
        facts = (
            f"capability_resolve: matched={len(matched)}/{total} subset_only=true",
        )
        if miss:
            facts = ("capability_resolve: miss (no keyword/role match; fail closed)",)
        return ResolveResult(
            matched=matched,
            query=query,
            role=role_norm,
            total_indexed=total,
            miss=miss,
            facts=facts,
        )

    def list_for_operator(
        self,
        *,
        kinds: Optional[Sequence[str]] = None,
        trust_tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Capped operator/Observability registry view - not a prompt dump-all."""
        lim = max(1, min(int(limit or 50), self.OPERATOR_MAX_LIMIT))
        off = max(0, int(offset or 0))
        rows = self._store.list_entries(
            kinds=kinds, trust_tier=trust_tier, limit=lim, offset=off
        )
        return {
            "entries": [e.model_dump(mode="json") for e in rows],
            "count": len(rows),
            "limit": lim,
            "offset": off,
            "total_indexed": self._store.count_entries(),
            "operator_view": True,
            "subset_only": True,
            "prompt_dump_forbidden": True,
        }


# Deliberately absent by design [REQ-CAPCAT-004]:
# - dump_all
# - list_all_for_prompt
# - get_full_catalog_for_prompt
FORBIDDEN_DUMP_ALL_ATTRS = frozenset(
    {
        "dump_all",
        "dump_all_for_prompt",
        "list_all_for_prompt",
        "get_full_catalog_for_prompt",
        "export_full_catalog_to_prompt",
        # CARD-228 progressive SKILL.md — never dump bodies at resolve
        "dump_all_skill_bodies",
        "load_all_skill_bodies_for_resolve",
        "resolve_with_full_skill_bodies",
    }
)
