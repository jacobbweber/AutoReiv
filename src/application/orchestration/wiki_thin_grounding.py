"""Wiki-thin fail-closed grounding [CARD-260].

Empty/thin vault on a topic -> HITL park with need sources OR Formulate
grounded only on matched wiki_note_* reads / create provenance.
Never invent Wiki paths/titles (Okta-class stale/fake Done).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional, Sequence

logger = logging.getLogger(__name__)

ACTION_SKIP = "skip_not_wiki"
ACTION_NEED_SOURCES = "need_sources_park"
ACTION_GROUNDED_ONLY = "grounded_only"
ACTION_PROCEED_WITH_HITS = "proceed_with_hits"

NEED_SOURCES_REASON = "wiki_need_sources"

_WIKI_ASK_RE = re.compile(
    r"\b(wiki|00_inbox|inbox note|wiki_note_|markdown note|vault note)\b",
    re.IGNORECASE,
)
_CREATE_ASK_RE = re.compile(
    r"\b(write|create|author|draft|stage|file)\b.*\b(note|wiki)\b"
    r"|\b(note|wiki)\b.*\b(write|create|author|draft|stage|file)\b",
    re.IGNORECASE,
)
_SOURCE_DEP_RE = re.compile(
    r"\b(summariz|from (the )?wiki|based on (existing |matched )?wiki"
    r"|using (only )?matched wiki|research .+ wiki|what (does|do) the wiki"
    r"|update (the )?existing|sources? needed|need sources)\b",
    re.IGNORECASE,
)
_PATH_RE = re.compile(
    r"(?P<path>(?:00_Inbox|01_Notes|02_Resources|notes|inbox|resources)"
    r"(?:/[\w.\-]+)+\.md)",
    re.IGNORECASE,
)
_TOPIC_STOP = frozenset(
    {
        "a", "an", "the", "write", "short", "wiki", "note", "notes", "in", "about",
        "using", "only", "matched", "done", "when", "i", "can", "open", "that",
        "via", "wiki_note_read", "wiki_note_create", "keep", "it", "under", "words",
        "00_inbox", "inbox", "summarizing", "summarize", "existing", "from", "to",
        "for", "with", "and", "or", "of", "on", "my", "me", "please", "create",
        "author", "draft", "file", "stage", "markdown", "vault",
        "what", "says", "said", "cited", "sources", "source", "obscure", "topic",
        "no", "vault", "maintenance", "server", "how", "works", "this", "job",
    }
)

# Tokens that may appear in topic bags but never alone prove vault grounding.
_WEAK_TOPIC_HITS = frozenset(
    {
        "maintenance", "quantum", "flute", "server", "general", "system", "update",
        "document", "summary", "overview", "guide", "intro", "introduction",
    }
)
_PROVENANCE_TOOLS = frozenset(
    {
        "wiki_note_create",
        "wiki_note_read",
        "tool.wiki_note_create",
        "tool.wiki_note_read",
    }
)


@dataclass(frozen=True)
class WikiGroundingDecision:
    """Deterministic thin-vault grounding decision [REQ-WIKITHIN-001]."""

    action: str
    thin: bool
    reason: str
    topic_query: str
    hit_paths: tuple[str, ...] = field(default_factory=tuple)
    matched_read_paths: tuple[str, ...] = field(default_factory=tuple)
    create_shaped: bool = False
    source_dependent: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "thin": self.thin,
            "reason": self.reason,
            "topic_query": self.topic_query,
            "hit_paths": list(self.hit_paths),
            "matched_read_paths": list(self.matched_read_paths),
            "create_shaped": self.create_shaped,
            "source_dependent": self.source_dependent,
            "need_sources": self.action == ACTION_NEED_SOURCES,
            "grounded_only": self.action in {ACTION_GROUNDED_ONLY, ACTION_PROCEED_WITH_HITS},
        }


def is_wiki_related_ask(intent: str | None) -> bool:
    text = (intent or "").strip()
    if not text:
        return False
    if _WIKI_ASK_RE.search(text):
        return True
    lower = text.lower()
    return "wiki_note_" in lower or "00_inbox" in lower


def is_wiki_create_ask(intent: str | None) -> bool:
    text = (intent or "").strip()
    if not text or not is_wiki_related_ask(text):
        return False
    return bool(_CREATE_ASK_RE.search(text))


def is_wiki_source_dependent_ask(intent: str | None) -> bool:
    text = (intent or "").strip()
    if not text:
        return False
    return bool(_SOURCE_DEP_RE.search(text))


def extract_topic_query(intent: str | None, *, max_terms: int = 8) -> str:
    """Crude topic bag for vault search (fail-closed; empty => thin)."""
    text = re.sub(r"[`*_#>\"]+", " ", (intent or ""))
    text = re.sub(r"\bdone[- ]?when\b.*", " ", text, flags=re.IGNORECASE)
    terms: list[str] = []
    for raw in re.findall(r"[A-Za-z0-9][A-Za-z0-9_\-]{1,}", text):
        t = raw.lower()
        if t in _TOPIC_STOP or t.isdigit():
            continue
        if t not in terms:
            terms.append(t)
        if len(terms) >= max_terms:
            break
    return " ".join(terms)


def normalize_wiki_path(path: str | None) -> str:
    p = (path or "").strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p.lstrip("/")


def _hit_text(hit: Mapping[str, Any]) -> str:
    parts = [
        str(hit.get("path") or ""),
        str(hit.get("title") or ""),
        str(hit.get("summary") or ""),
        str(hit.get("preview") or ""),
        " ".join(str(x) for x in (hit.get("tags") or [])),
    ]
    return " ".join(parts).lower()


def filter_hits_for_topic(
    hits: Sequence[Mapping[str, Any]] | None,
    topic_query: str | None,
) -> list[dict[str, Any]]:
    """Keep only hits that share a distinctive topic token (len>=5 or digit-bearing)."""
    raw_tokens = [
        tok
        for tok in (topic_query or "").lower().replace("-", " ").split()
        if tok and tok not in _TOPIC_STOP
    ]
    # Prefer distinctive anchors (digit-bearing or not weak); fall back to all.
    anchors = [
        tok
        for tok in raw_tokens
        if any(ch.isdigit() for ch in tok)
        or (len(tok) >= 5 and tok not in _WEAK_TOPIC_HITS)
    ]
    tokens = anchors or [tok for tok in raw_tokens if len(tok) >= 5]
    if not tokens:
        return []
    kept: list[dict[str, Any]] = []
    for hit in hits or []:
        if not isinstance(hit, Mapping):
            continue
        blob = _hit_text(hit)
        if any(tok in blob for tok in tokens):
            kept.append(dict(hit))
    return kept


def paths_from_search_hits(hits: Sequence[Mapping[str, Any]] | None) -> tuple[str, ...]:
    out: list[str] = []
    for hit in hits or []:
        if not isinstance(hit, Mapping):
            continue
        path = normalize_wiki_path(
            str(hit.get("path") or hit.get("relative_path") or hit.get("note_path") or "")
        )
        if path and path not in out:
            out.append(path)
    return tuple(out)


def assess_wiki_thin_grounding(
    intent: str | None,
    hits: Sequence[Mapping[str, Any]] | None = None,
    *,
    matched_read_paths: Sequence[str] | None = None,
    thin_hit_max: int = 0,
) -> WikiGroundingDecision:
    """
    Fail-closed vault grounding [REQ-WIKITHIN-001 / REQ-WIKITHIN-002].

    - Non-wiki asks => skip
    - Empty/thin + source-dependent => need_sources_park
    - Empty/thin + create-shaped => grounded_only (create provenance later)
    - Empty/thin + other wiki => need_sources_park (fail closed)
    - Has hits => proceed_with_hits (RAG on those paths only)
    """
    topic = extract_topic_query(intent)
    filtered = filter_hits_for_topic(hits, topic)
    hit_paths = paths_from_search_hits(filtered)
    reads = tuple(
        normalize_wiki_path(p)
        for p in (matched_read_paths or [])
        if normalize_wiki_path(p)
    )
    create_shaped = is_wiki_create_ask(intent)
    source_dep = is_wiki_source_dependent_ask(intent)

    if not is_wiki_related_ask(intent):
        return WikiGroundingDecision(
            action=ACTION_SKIP,
            thin=False,
            reason="not_wiki_ask",
            topic_query=topic,
            hit_paths=hit_paths,
            matched_read_paths=reads,
            create_shaped=create_shaped,
            source_dependent=source_dep,
        )

    thin = len(hit_paths) <= thin_hit_max
    # Matched wiki_note_read paths count as grounding even if search was thin.
    if reads and thin:
        return WikiGroundingDecision(
            action=ACTION_GROUNDED_ONLY,
            thin=True,
            reason="thin_vault_grounded_on_matched_reads",
            topic_query=topic,
            hit_paths=hit_paths,
            matched_read_paths=reads,
            create_shaped=create_shaped,
            source_dependent=source_dep,
        )

    if not thin:
        return WikiGroundingDecision(
            action=ACTION_PROCEED_WITH_HITS,
            thin=False,
            reason="vault_hits_present",
            topic_query=topic,
            hit_paths=hit_paths,
            matched_read_paths=reads,
            create_shaped=create_shaped,
            source_dependent=source_dep,
        )

    # Thin vault.
    if source_dep and not create_shaped:
        return WikiGroundingDecision(
            action=ACTION_NEED_SOURCES,
            thin=True,
            reason=NEED_SOURCES_REASON + ":source_dependent_thin",
            topic_query=topic,
            hit_paths=hit_paths,
            matched_read_paths=reads,
            create_shaped=create_shaped,
            source_dependent=source_dep,
        )
    if create_shaped:
        return WikiGroundingDecision(
            action=ACTION_GROUNDED_ONLY,
            thin=True,
            reason="thin_vault_create_grounded_only",
            topic_query=topic,
            hit_paths=hit_paths,
            matched_read_paths=reads,
            create_shaped=create_shaped,
            source_dependent=source_dep,
        )
    return WikiGroundingDecision(
        action=ACTION_NEED_SOURCES,
        thin=True,
        reason=NEED_SOURCES_REASON + ":thin_fail_closed",
        topic_query=topic,
        hit_paths=hit_paths,
        matched_read_paths=reads,
        create_shaped=create_shaped,
        source_dependent=source_dep,
    )


def probe_vault_hits(
    wiki_root: str | None,
    intent: str | None,
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Best-effort WikiStore search; empty on any failure (fail-closed thin)."""
    topic = extract_topic_query(intent)
    if not wiki_root or not topic:
        return []
    try:
        from src.domain.wiki.store import WikiStore

        store = WikiStore(root_dir=wiki_root)
        hits = store.search_notes(query=topic, limit=limit) or []
        return [h for h in hits if isinstance(h, dict)]
    except Exception as exc:  # noqa: BLE001
        logger.debug("wiki thin probe soft-fail: %s", exc)
        return []


def format_need_sources_park_message(
    decision: WikiGroundingDecision,
    *,
    job_id: str | None = None,
) -> str:
    topic = decision.topic_query or "(unknown topic)"
    job_bit = f" Job {job_id}." if job_id else ""
    return (
        f"HITL park — need sources.{job_bit} "
        f"Wiki is empty/thin for topic '{topic}'. "
        "Fail-closed grounding: will not invent Wiki paths/titles. "
        "Provide sources or approve after vault notes exist, then resume."
    )


def format_grounding_constraint_block(decision: WikiGroundingDecision) -> str:
    """Inject into Formulate/Execute assignment — never invent paths."""
    allowed = list(decision.matched_read_paths) + list(decision.hit_paths)
    allowed_s = (
        ", ".join(f"`{p}`" for p in allowed)
        if allowed
        else "(none yet — only paths returned by wiki_note_create/read)"
    )
    return (
        "WIKI GROUNDING CONSTRAINT [CARD-260 / fail-closed]:\n"
        f"- action={decision.action}; thin={decision.thin}; reason={decision.reason}\n"
        f"- Allowed grounding paths: {allowed_s}\n"
        "- Never invent Wiki paths or titles. Do not claim a note path unless "
        "wiki_note_read or wiki_note_create returned it in this Job.\n"
        "- If you need sources that are not in the allowed list, park with need sources "
        "instead of fabricating a path (Okta-class ban)."
    )


def collect_provenanced_paths_from_tool_result(
    tool_name: str | None,
    result: Any,
) -> list[str]:
    """Extract note paths from wiki_note_create / wiki_note_read tool outputs."""
    name = (tool_name or "").strip()
    if (
        name not in _PROVENANCE_TOOLS
        and not name.endswith("wiki_note_create")
        and not name.endswith("wiki_note_read")
    ):
        return []
    payload: Any = result
    if isinstance(result, str):
        text = result.strip()
        try:
            payload = json.loads(text)
        except Exception:
            return [normalize_wiki_path(m.group("path")) for m in _PATH_RE.finditer(text)]
    paths: list[str] = []
    if isinstance(payload, Mapping):
        for key in ("path", "relative_path", "note_path"):
            p = normalize_wiki_path(str(payload.get(key) or ""))
            if p and p not in paths:
                paths.append(p)
        for nest_key in ("result", "data", "note"):
            nested = payload.get(nest_key)
            if isinstance(nested, Mapping):
                for key in ("path", "relative_path", "note_path"):
                    p = normalize_wiki_path(str(nested.get(key) or ""))
                    if p and p not in paths:
                        paths.append(p)
    elif isinstance(payload, list):
        for item in payload:
            if isinstance(item, Mapping):
                p = normalize_wiki_path(
                    str(item.get("path") or item.get("relative_path") or "")
                )
                if p and p not in paths:
                    paths.append(p)
    return paths


def extract_claimed_wiki_paths(text: str | None) -> list[str]:
    out: list[str] = []
    for m in _PATH_RE.finditer(text or ""):
        p = normalize_wiki_path(m.group("path"))
        if not p or "..." in p:
            continue
        if p and p not in out:
            out.append(p)
    return out


def ungrounded_claimed_paths(
    text: str | None,
    provenanced: Sequence[str] | None,
) -> list[str]:
    """Paths claimed in assistant text that were not tool-provenanced [REQ-WIKITHIN-002]."""
    allowed = {normalize_wiki_path(p) for p in (provenanced or []) if normalize_wiki_path(p)}
    allowed_l = {p.lower() for p in allowed}
    bad: list[str] = []
    for claim in extract_claimed_wiki_paths(text):
        if claim.lower() not in allowed_l:
            bad.append(claim)
    return bad


def format_ungrounded_claim_honesty(
    ungrounded: Sequence[str],
    provenanced: Sequence[str] | None = None,
    *,
    job_id: str | None = None,
) -> str:
    job_bit = f" Job {job_id}." if job_id else ""
    bad = ", ".join(f"`{p}`" for p in ungrounded) or "(unknown)"
    ok = ", ".join(f"`{p}`" for p in (provenanced or []) if p) or "(none)"
    return (
        f"Not done — ungrounded Wiki path claim.{job_bit} "
        f"Invented/unprovenanced path(s): {bad}. "
        f"Tool-provenanced paths this Job: {ok}. "
        "Fail-closed [CARD-260]: Chat may only claim paths from wiki_note_create/read."
    )


def apply_standing_wiki_thin_grounding(
    orch: Any,
    job: Any,
    *,
    wiki_root: str | None,
    intent: str | None = None,
    matched_read_paths: Sequence[str] | None = None,
    park: bool = True,
) -> WikiGroundingDecision:
    """
    Probe vault + decide; optionally HITL-park Formulate when need_sources [REQ-WIKITHIN-001].
    Stamps memory facts + journey event. Never invents paths.
    """
    goal = intent if intent is not None else str(getattr(job, "goal", "") or "")
    job_id = str(getattr(job, "id", "") or "")
    hits = probe_vault_hits(wiki_root, goal)
    decision = assess_wiki_thin_grounding(
        goal,
        hits,
        matched_read_paths=matched_read_paths,
    )

    try:
        facts = [
            f"wiki_thin_grounding: action={decision.action}",
            f"wiki_thin_grounding: thin={decision.thin}",
            f"wiki_thin_grounding: reason={decision.reason}",
            f"wiki_thin_grounding: topic={decision.topic_query[:200]}",
            f"wiki_thin_grounding: hit_paths={list(decision.hit_paths)[:12]}",
        ]
        persist = getattr(orch, "_persist_phase_memory", None)
        phases = []
        try:
            phases = orch._store.list_phases_for_job(job_id)  # noqa: SLF001
        except Exception:
            phases = []
        formulate = next(
            (
                p
                for p in phases
                if str(getattr(p, "name", "") or "").lower().startswith("formulate")
            ),
            phases[0] if phases else None,
        )
        if callable(persist) and formulate is not None:
            persist(formulate, facts)
        commit = getattr(orch, "_commit_checkpoint", None)
        if callable(commit) and formulate is not None:
            commit(
                formulate,
                verifier_status="none",
                hitl_park_state=decision.action == ACTION_NEED_SOURCES,
                last_fail_reason=(
                    NEED_SOURCES_REASON
                    if decision.action == ACTION_NEED_SOURCES
                    else None
                ),
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("wiki grounding memory/checkpoint soft-fail: %s", exc)

    ev = getattr(getattr(orch, "_store", None), "save_standing_journey_event", None)
    if callable(ev) and job_id:
        try:
            ev(
                job_id=job_id,
                kind="wiki_thin_grounding",
                payload=decision.as_dict(),
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("wiki grounding journey soft-fail: %s", exc)

    if park and decision.action == ACTION_NEED_SOURCES and job_id:
        try:
            phases = orch._store.list_phases_for_job(job_id)  # noqa: SLF001
            formulate = next(
                (
                    p
                    for p in phases
                    if str(getattr(p, "name", "") or "").lower().startswith("formulate")
                ),
                None,
            )
            if formulate is not None:
                st = getattr(
                    getattr(formulate, "status", None),
                    "value",
                    str(getattr(formulate, "status", "")),
                )
                if st in {"queued", "running", "waiting_approval"}:
                    park_fn = getattr(orch, "park_phase", None)
                    if callable(park_fn):
                        park_fn(formulate.id, verifier_status="none")
        except Exception as exc:  # noqa: BLE001
            logger.warning("wiki need_sources park failed: %s", exc)

    cache = getattr(orch, "_wiki_grounding", None)
    if not isinstance(cache, dict):
        cache = {}
        try:
            orch._wiki_grounding = cache  # noqa: SLF001
        except Exception:
            pass
    if isinstance(cache, dict) and job_id:
        cache[job_id] = decision

    return decision


def grounding_for_job(orch: Any, job_id: str) -> Optional[WikiGroundingDecision]:
    cache = getattr(orch, "_wiki_grounding", None)
    if isinstance(cache, dict):
        dec = cache.get(job_id)
        if isinstance(dec, WikiGroundingDecision):
            return dec
    return None


__all__ = [
    "ACTION_GROUNDED_ONLY",
    "ACTION_NEED_SOURCES",
    "ACTION_PROCEED_WITH_HITS",
    "ACTION_SKIP",
    "NEED_SOURCES_REASON",
    "WikiGroundingDecision",
    "apply_standing_wiki_thin_grounding",
    "assess_wiki_thin_grounding",
    "collect_provenanced_paths_from_tool_result",
    "extract_claimed_wiki_paths",
    "extract_topic_query",
    "format_grounding_constraint_block",
    "format_need_sources_park_message",
    "format_ungrounded_claim_honesty",
    "grounding_for_job",
    "is_wiki_create_ask",
    "is_wiki_related_ask",
    "is_wiki_source_dependent_ask",
    "normalize_wiki_path",
    "filter_hits_for_topic",
    "paths_from_search_hits",
    "probe_vault_hits",
    "ungrounded_claimed_paths",
]
