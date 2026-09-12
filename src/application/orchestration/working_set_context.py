"""Phase-scoped working-set context for standing Job/Phase turns [CARD-229 / CARD-253].

Each Job/Phase turn carries:
  - phase goal
  - matched capability metadata (no unbound skill bodies)
  - bound skill body for THIS phase only
  - this-phase memory.db facts
  - prior phases as short durable notes (not raw tool dumps)

Aligns with M12 / CARD-041 ContextCompactor truncation discipline (max_tool_chars=8000
style stripping of tool dumps; short condensed notes instead of verbatim history).

AGENTS.md invariant: Chat still lists that agent's ticked tools every turn — this
module only shapes the phase assignment user prompt; it must never hide tool schemas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Mapping, Optional, Sequence

# M12 / ContextCompactor default (src/application/kernel/context_compactor.py).
M12_MAX_TOOL_CHARS = 8000

# Short durable notes for prior phases (not raw packets / tool dumps).
DURABLE_NOTE_MAX_CHARS = 400

BOUND_SKILL_BODY_MAX_CHARS = 8000

# CARD-253: memory facts / ledger lines must stay short — never full Chat transcripts.
MEMORY_FACT_MAX_CHARS = 500
TRANSCRIPT_DUMP_MARKER = "TRANSCRIPT_DUMP_REJECTED"

_TRANSCRIPT_ROLE_PATTERNS = (
    re.compile(r"(?m)^\s*(system|user|assistant|tool|human|ai)\s*:", re.IGNORECASE),
    re.compile(r"(?i)\b(role\s*[:=]\s*['\"]?(user|assistant|system|tool))\b"),
    re.compile(r"(?i)\b(chat\s*transcript|session\s*transcript|full\s*transcript)\b"),
    re.compile(r"(?i)\bget_session_transcript\b"),
    re.compile(r"(?i)\b(message\s*history|conversation\s*history)\b"),
)


def looks_like_transcript_dump(text: str) -> bool:
    """True when text looks like a full Chat/session transcript dumped as memory [REQ-LRCTX-003]."""
    raw = (text or "").strip()
    if not raw:
        return False
    # Long multi-turn role dumps are theatre even if under a soft length cap later.
    role_hits = sum(1 for pat in _TRANSCRIPT_ROLE_PATTERNS[:2] for _ in pat.finditer(raw))
    if role_hits >= 3:
        return True
    if any(pat.search(raw) for pat in _TRANSCRIPT_ROLE_PATTERNS[2:]):
        return True
    # Many alternating role lines.
    lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    role_lines = sum(
        1
        for ln in lines
        if re.match(r"(?i)^(system|user|assistant|tool|human|ai)\s*:", ln)
    )
    if role_lines >= 4 and len(raw) > 400:
        return True
    if len(raw) > MEMORY_FACT_MAX_CHARS * 4 and role_lines >= 2:
        return True
    return False


def sanitize_memory_fact(
    text: str,
    *,
    max_chars: int = MEMORY_FACT_MAX_CHARS,
    reject_transcripts: bool = True,
) -> str | None:
    """Sanitize a candidate memory/ledger fact.

    Returns None when the value is a transcript dump masquerading as memory
    (fail closed for [REQ-LRCTX-003]). Otherwise returns a short dump-free fact.
    """
    raw = (text or "").strip()
    if not raw:
        return None
    if reject_transcripts and looks_like_transcript_dump(raw):
        return None
    cleaned = strip_tool_dumps(raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned:
        return None
    if len(cleaned) > max_chars:
        omitted = len(cleaned) - max_chars
        cleaned = (
            cleaned[:max_chars]
            + f" ... [TRUNCATED: {omitted} characters omitted for context budget] ..."
        )
    return cleaned


def assert_not_transcript_memory(text: str) -> str:
    """Raise ValueError when a full transcript tries to enter memory [REQ-LRCTX-003]."""
    if looks_like_transcript_dump(text):
        raise ValueError(
            "Full Chat/session transcript must not masquerade as memory "
            f"[{TRANSCRIPT_DUMP_MARKER} / CARD-253 / REQ-LRCTX-003]"
        )
    out = sanitize_memory_fact(text, reject_transcripts=True)
    if out is None:
        raise ValueError(
            "Empty or rejected memory fact after sanitize "
            f"[{TRANSCRIPT_DUMP_MARKER} / CARD-253]"
        )
    return out


_TOOL_DUMP_PATTERNS = (
    re.compile(r"\[Tool Output:[^\]]*\]:.*?(?=\n\[|\n\n|\Z)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\{[^{}]*\"tool_call\"[^{}]*\}", re.IGNORECASE | re.DOTALL),
    re.compile(r"\{[^{}]*\"function_response\"[^{}]*\}", re.IGNORECASE | re.DOTALL),
    re.compile(r"bound skill [^\n]+:\n.*?(?=\nPhase |\nPRIOR |\Z)", re.IGNORECASE | re.DOTALL),
)


def strip_tool_dumps(text: str) -> str:
    """Remove tool-dump / unbound skill-body blobs from prior context [REQ-WSCTX-002]."""
    cleaned = text or ""
    for pat in _TOOL_DUMP_PATTERNS:
        cleaned = pat.sub("", cleaned)
    # Drop huge single-line blobs that look like dumped JSON tool payloads.
    lines: List[str] = []
    for line in cleaned.splitlines():
        stripped = line.strip()
        if len(stripped) > 600 and (
            stripped.startswith("{")
            or stripped.startswith("[")
            or "tool_call" in stripped.lower()
            or "function_response" in stripped.lower()
        ):
            omitted = len(stripped) - 120
            lines.append(
                stripped[:120]
                + f" ... [TRUNCATED: {omitted} characters omitted for context budget] ..."
            )
            continue
        lines.append(line)
    out = "\n".join(lines)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def distill_durable_note(
    *,
    phase_name: str,
    phase_index: int,
    raw_output: str,
    max_chars: int = DURABLE_NOTE_MAX_CHARS,
) -> str:
    """Prior phase -> short durable note (M12-aligned; no raw tool dumps) [REQ-WSCTX-002]."""
    cleaned = strip_tool_dumps(raw_output or "")
    # Prefer first meaningful sentence-ish content.
    compact = re.sub(r"\s+", " ", cleaned).strip()
    if len(compact) > max_chars:
        omitted = len(compact) - max_chars
        compact = (
            compact[:max_chars]
            + f" ... [TRUNCATED: {omitted} characters omitted for context budget] ..."
        )
    label = f"Phase {phase_index + 1} ({phase_name or 'phase'})"
    if not compact:
        return f"{label}: (no durable note)"
    return f"{label}: {compact}"


def matched_metadata_only(entries: Sequence[Mapping[str, Any]]) -> List[dict[str, Any]]:
    """Keep resolve-style metadata only; never skill bodies."""
    body_keys = {
        "instructions",
        "body",
        "content",
        "skill_md",
        "skill_body",
        "runbook",
        "runbook_body",
        "markdown",
        "full_text",
        "playbook",
    }
    out: List[dict[str, Any]] = []
    for raw in entries or []:
        row = dict(raw)
        for k in list(row.keys()):
            if str(k).strip().lower() in body_keys:
                row.pop(k, None)
        meta = row.get("metadata")
        if isinstance(meta, Mapping):
            row["metadata"] = {
                mk: mv
                for mk, mv in dict(meta).items()
                if str(mk).strip().lower() not in body_keys
                and not (isinstance(mv, str) and len(mv) > 400)
            }
        row.setdefault("metadata_only", True)
        row.setdefault("body_loaded", False)
        out.append(row)
    return out


def filter_this_phase_memory_facts(
    facts: Sequence[str],
    *,
    phase_index: int,
) -> List[str]:
    """Keep memory.db lines that belong to this phase index when attribute-prefixed.

    CARD-253: drop transcript dumps masquerading as memory; keep short ledger facts only.
    """
    prefix = f"phase_{phase_index}_"
    selected: List[str] = []
    for f in facts or []:
        sanitized = sanitize_memory_fact(str(f))
        if sanitized:
            selected.append(sanitized)
    phased = [
        f
        for f in selected
        if f.lower().startswith(prefix) or f": {prefix}" in f.lower()
    ]
    # If caller already scoped facts, keep them; else keep all short job facts as this-phase input
    # only when none match the prefix (first phase / unprefixed recalls).
    if phased:
        return phased
    # Unprefixed short facts are allowed as this-phase working memory (CARD-226 lines).
    return [
        f
        for f in selected
        if len(f) <= MEMORY_FACT_MAX_CHARS and "tool output" not in f.lower()
    ]


def prior_notes_from_memory_facts(
    facts: Sequence[str],
    *,
    current_phase_index: int,
) -> List[str]:
    """Convert earlier-phase memory.db facts into short durable notes.

    CARD-253: never promote a full transcript dump into prior notes.
    """
    notes: List[str] = []
    for fact in facts or []:
        text = str(fact).strip()
        if not text:
            continue
        if looks_like_transcript_dump(text):
            continue
        lower = text.lower()
        # Skip current phase facts.
        if lower.startswith(f"phase_{current_phase_index}_"):
            continue
        m = re.match(r"phase_(\d+)_", lower)
        if m:
            idx = int(m.group(1))
            if idx >= current_phase_index:
                continue
            notes.append(
                distill_durable_note(
                    phase_name=f"phase_{idx}",
                    phase_index=idx,
                    raw_output=text,
                )
            )
        else:
            # Generic prior durable fact (already short from memory.db).
            cleaned = sanitize_memory_fact(text) or strip_tool_dumps(text)
            if cleaned and len(cleaned) <= DURABLE_NOTE_MAX_CHARS:
                notes.append(cleaned)
            elif cleaned:
                notes.append(
                    distill_durable_note(
                        phase_name="prior",
                        phase_index=max(0, current_phase_index - 1),
                        raw_output=cleaned,
                    )
                )
    # De-dupe while preserving order.
    seen: set[str] = set()
    uniq: List[str] = []
    for n in notes:
        if n not in seen:
            seen.add(n)
            uniq.append(n)
    return uniq


@dataclass
class PhaseWorkingSet:
    """Working set carried on one Job/Phase turn [REQ-WSCTX-001]."""

    job_goal: str
    phase_name: str
    phase_index: int
    phase_count: int
    phase_goal: str
    matched_metadata: List[dict[str, Any]] = field(default_factory=list)
    bound_skill_id: Optional[str] = None
    bound_skill_body: Optional[str] = None
    this_phase_memory_facts: List[str] = field(default_factory=list)
    prior_phase_notes: List[str] = field(default_factory=list)

    @property
    def has_bound_skill_body(self) -> bool:
        return bool((self.bound_skill_body or "").strip())


def build_phase_working_set(
    *,
    job: Any,
    phase: Any,
    phase_count: int,
    matched_metadata: Sequence[Mapping[str, Any]] | None = None,
    bound_skill_id: Optional[str] = None,
    bound_skill_body: Optional[str] = None,
    this_phase_memory_facts: Sequence[str] | None = None,
    prior_phase_notes: Sequence[str] | None = None,
    all_memory_facts: Sequence[str] | None = None,
) -> PhaseWorkingSet:
    """Assemble phase-scoped working set for standing Chat/Routines [REQ-WSCTX-001]."""
    phase_index = int(getattr(phase, "index", 0) or 0)
    phase_name = str(getattr(phase, "name", "") or "")
    phase_goal = str(
        getattr(phase, "success_rule", None) or getattr(phase, "name", None) or ""
    )
    job_goal = str(getattr(job, "goal", "") or "")

    meta = matched_metadata_only(matched_metadata or [])

    body = (bound_skill_body or None)
    if body is not None:
        body = body.strip()
        if len(body) > BOUND_SKILL_BODY_MAX_CHARS:
            omitted = len(body) - BOUND_SKILL_BODY_MAX_CHARS
            body = (
                body[:BOUND_SKILL_BODY_MAX_CHARS]
                + f"\n\n... [TRUNCATED: {omitted} characters omitted for context budget] ..."
            )

    facts_in = list(this_phase_memory_facts or [])
    if all_memory_facts is not None and not facts_in:
        facts_in = filter_this_phase_memory_facts(all_memory_facts, phase_index=phase_index)

    notes_in = [strip_tool_dumps(n) for n in (prior_phase_notes or []) if str(n).strip()]
    notes_in = [n for n in notes_in if n]
    if all_memory_facts is not None and not notes_in and phase_index > 0:
        notes_in = prior_notes_from_memory_facts(
            all_memory_facts, current_phase_index=phase_index
        )

    # Hard exclude: never let prior notes contain a second skill body marker block.
    safe_notes: List[str] = []
    for n in notes_in:
        if "bound skill" in n.lower() and len(n) > DURABLE_NOTE_MAX_CHARS:
            safe_notes.append(
                distill_durable_note(
                    phase_name="prior",
                    phase_index=max(0, phase_index - 1),
                    raw_output=n,
                )
            )
        else:
            if len(n) > DURABLE_NOTE_MAX_CHARS + 80:
                safe_notes.append(
                    distill_durable_note(
                        phase_name="prior",
                        phase_index=max(0, phase_index - 1),
                        raw_output=n,
                    )
                )
            else:
                safe_notes.append(n)

    return PhaseWorkingSet(
        job_goal=job_goal,
        phase_name=phase_name,
        phase_index=phase_index,
        phase_count=int(phase_count),
        phase_goal=phase_goal,
        matched_metadata=meta,
        bound_skill_id=bound_skill_id,
        bound_skill_body=body,
        this_phase_memory_facts=[str(f).strip() for f in facts_in if str(f).strip()],
        prior_phase_notes=safe_notes,
    )


def format_phase_working_set_prompt(ws: PhaseWorkingSet) -> str:
    """Render working set into the phase assignment user prompt [REQ-WSCTX-003]."""
    meta_lines: List[str] = []
    for row in ws.matched_metadata:
        rid = row.get("id") or "?"
        title = row.get("title") or row.get("name") or rid
        risk = row.get("risk") or row.get("risk_level") or ""
        hitl = row.get("requires_hitl")
        meta_lines.append(
            f"- {rid}: {title} (risk={risk}, hitl={hitl}, metadata_only=true)"
        )
    meta_block = "\n".join(meta_lines) if meta_lines else "None"

    notes_block = "\n".join(ws.prior_phase_notes) if ws.prior_phase_notes else "None (first phase)"
    facts_block = (
        "\n".join(ws.this_phase_memory_facts) if ws.this_phase_memory_facts else "None"
    )

    if ws.bound_skill_body:
        skill_block = (
            f"BOUND SKILL ({ws.bound_skill_id or 'selected'}):\n"
            f"{ws.bound_skill_body}"
        )
    else:
        skill_block = "BOUND SKILL: None (metadata only; no body bound for this phase)"

    return (
        f"You are executing phase {ws.phase_index + 1}/{ws.phase_count} "
        f"of the goal: '{ws.job_goal}'.\n"
        f"PHASE: {ws.phase_name}\n"
        f"PHASE GOAL / SUCCESS RULE: {ws.phase_goal or ws.phase_name}\n"
        f"MATCHED CAPABILITY METADATA (no unbound skill bodies):\n{meta_block}\n"
        f"{skill_block}\n"
        f"THIS-PHASE MEMORY.DB FACTS:\n{facts_block}\n"
        f"PRIOR PHASE DURABLE NOTES (not raw tool dumps):\n{notes_block}"
    )


def resolve_matched_metadata_for_job(orch: Any, job_id: str) -> List[dict[str, Any]]:
    """Best-effort matched metadata from standing orchestrator (progressive views)."""
    ids_fn = getattr(orch, "matched_capability_ids_for_job", None)
    ids: List[str] = list(ids_fn(job_id) or []) if callable(ids_fn) else []
    rows: List[dict[str, Any]] = []
    resolver = getattr(orch, "_capability_resolver", None)
    store = getattr(resolver, "_store", None) if resolver is not None else None
    getter = getattr(store, "get_entry", None) if store is not None else None
    for cid in ids:
        if callable(getter):
            entry = getter(cid)
            if entry is not None:
                try:
                    from src.application.capabilities.progressive_skills import (
                        entry_to_resolve_view,
                    )

                    rows.append(entry_to_resolve_view(entry))
                    continue
                except Exception:
                    pass
        rows.append(
            {
                "id": cid,
                "title": cid,
                "metadata_only": True,
                "body_loaded": False,
            }
        )
    return matched_metadata_only(rows)


def rebuild_working_set_after_resume(
    *,
    job: Any,
    phase: Any,
    phase_count: int,
    all_memory_facts: Sequence[str] | None = None,
    matched_metadata: Sequence[Mapping[str, Any]] | None = None,
    bound_skill_id: Optional[str] = None,
    bound_skill_body: Optional[str] = None,
    session_transcript: Sequence[str] | Mapping[str, Any] | str | None = None,
) -> PhaseWorkingSet:
    """Rebuild phase N+1 working set after kill/resume [CARD-253 / REQ-LRCTX-002].

    Uses ledger/memory.db facts + progressive skill bind only.
    Explicitly ignores session_transcript arguments (anti-theatre): full prior
    dumps must not masquerade as memory.
    """
    if session_transcript is not None:
        # Fail closed when caller tries to feed transcript as working-set prior.
        blob = session_transcript
        if isinstance(blob, Mapping):
            blob = str(blob)
        elif not isinstance(blob, str):
            blob = "\n".join(str(x) for x in blob)
        if looks_like_transcript_dump(str(blob)) or len(str(blob).strip()) > MEMORY_FACT_MAX_CHARS:
            raise ValueError(
                "session_transcript cannot seed working set after resume "
                f"[{TRANSCRIPT_DUMP_MARKER} / CARD-253 / REQ-LRCTX-003]; "
                "use memory.db ledger facts only"
            )
        # Even short non-transcript leftovers are ignored — memory.db is authority.
    facts = list(all_memory_facts or [])
    # Drop any transcript-shaped lines that leaked into the fact list.
    safe_facts = [f for f in (sanitize_memory_fact(x) or "" for x in facts) if f]
    return build_phase_working_set(
        job=job,
        phase=phase,
        phase_count=phase_count,
        matched_metadata=matched_metadata,
        bound_skill_id=bound_skill_id,
        bound_skill_body=bound_skill_body,
        all_memory_facts=safe_facts,
        prior_phase_notes=None,  # rebuild from memory facts
    )

