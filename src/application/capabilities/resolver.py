"""
Match-only capability catalog resolver [CARD-217 / REQ-CAPCAT-003..004].

Returns a matched subset for intent/role/keyword. Never dumps the full catalog
into a prompt payload. Operator registry listing is separate and capped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Protocol, Sequence

from src.domain.capabilities.models import CapabilityIndexEntry, CapabilityKind, TrustTier


class CapabilityCatalogStore(Protocol):
    def upsert_entry(self, entry: CapabilityIndexEntry) -> CapabilityIndexEntry: ...

    def get_entry(self, entry_id: str) -> Optional[CapabilityIndexEntry]: ...
    def delete_entry(self, entry_id: str) -> bool: ...

    def list_entries(
        self,
        *,
        kinds: Optional[Sequence[str]] = None,
        trust_tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[CapabilityIndexEntry]: ...

    def count_entries(self) -> int: ...


ENGLISH_STOPWORDS = frozenset(
    {
        "a",
        "about",
        "above",
        "after",
        "again",
        "against",
        "all",
        "am",
        "an",
        "and",
        "any",
        "are",
        "as",
        "at",
        "be",
        "because",
        "been",
        "before",
        "being",
        "below",
        "between",
        "both",
        "but",
        "by",
        "can",
        "cannot",
        "could",
        "did",
        "do",
        "does",
        "doing",
        "down",
        "during",
        "each",
        "few",
        "for",
        "from",
        "further",
        "had",
        "has",
        "have",
        "having",
        "he",
        "her",
        "here",
        "hers",
        "herself",
        "him",
        "himself",
        "his",
        "how",
        "i",
        "if",
        "in",
        "into",
        "is",
        "it",
        "its",
        "itself",
        "me",
        "more",
        "most",
        "my",
        "myself",
        "no",
        "nor",
        "not",
        "of",
        "off",
        "on",
        "once",
        "only",
        "or",
        "other",
        "our",
        "ours",
        "ourselves",
        "out",
        "over",
        "own",
        "same",
        "she",
        "should",
        "so",
        "some",
        "such",
        "than",
        "that",
        "the",
        "their",
        "theirs",
        "them",
        "themselves",
        "then",
        "there",
        "these",
        "they",
        "this",
        "those",
        "through",
        "to",
        "too",
        "under",
        "until",
        "up",
        "very",
        "was",
        "we",
        "were",
        "what",
        "when",
        "where",
        "which",
        "while",
        "who",
        "whom",
        "why",
        "with",
        "would",
        "you",
        "your",
        "yours",
        "yourself",
        "yourselves",
    }
)

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokenize(text: str) -> List[str]:
    toks = [t.lower() for t in _TOKEN_RE.findall(text or "") if t]
    raw = (text or "").strip().lower()
    if "_" in raw and raw not in toks:
        toks.append(raw)
    return toks


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
        trusted_only: bool = False,
    ) -> ResolveResult:
        """Match intent/role/keywords to a subset. Empty intent -> miss, not dump-all.

        CARD-255: standing Job formulate passes trusted_only=True so candidates
        never auto-match into a Job (no auto-trust). Operator/Forge discovery
        keeps trusted_only=False / Forge candidate queue.
        """
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
        if trusted_only:
            # Standing Jobs: trusted only - never auto-trust candidates [CARD-255 / REQ-SSQ-003].
            filtered = []
            for entry in candidates:
                tier = getattr(entry.trust_tier, "value", entry.trust_tier)
                if str(tier).lower() == TrustTier.TRUSTED.value:
                    filtered.append(entry)
            candidates = filtered
        raw_tokens = set(_tokenize(query))
        tokens = {t for t in raw_tokens if t not in ENGLISH_STOPWORDS and len(t) > 1} or raw_tokens
        role_norm = (role or "").strip().lower() or None

        scored: List[tuple[int, int, CapabilityIndexEntry]] = []
        for entry in candidates:
            score = 0
            kw = ({str(x).lower() for x in (entry.keywords or [])}) - ENGLISH_STOPWORDS
            roles = {str(x).lower() for x in (entry.roles or [])}
            name_tokens = set(_tokenize(entry.name)) - ENGLISH_STOPWORDS
            summary_tokens = set(_tokenize(entry.summary)) - ENGLISH_STOPWORDS
            substantive_matches: set[str] = set()
            if tokens:
                matched_kw = tokens & kw
                matched_name = tokens & name_tokens
                matched_summary = tokens & summary_tokens

                # Direct match in tool/agent name is primary intent indicator
                score += 5 * len(matched_name)
                # Specific keyword match
                score += 3 * len(matched_kw)
                # Summary match (substantive non-stopword tokens only)
                score += 1 * len(matched_summary)

                # Compound bonus: matching multiple distinct tokens across name/keywords
                substantive_matches = matched_name | matched_kw
                if len(substantive_matches) > 1:
                    score += 4 * (len(substantive_matches) - 1)

            if role_norm and role_norm in roles:
                score += 4
            if score > 0:
                scored.append((score, len(substantive_matches), entry))

        scored.sort(key=lambda pair: (-pair[0], -pair[1], pair[2].name.lower(), pair[2].id))
        matched = tuple(entry for _, _, entry in scored[:lim])
        miss = len(matched) == 0
        facts = (
            f"capability_resolve: matched={len(matched)}/{total} subset_only=true trusted_only={str(bool(trusted_only)).lower()}",
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
