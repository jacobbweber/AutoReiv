"""Standing research-before-plan on capability gap only [CARD-231].

After intake catalog resolve:
  thin/gap  → insert Research phase before Formulate/Execute
  sufficient → skip research (Formulate/Execute only)

Research writes facts into <agent>_memory.db and may propose catalog gaps.
It never writes trusted skills/tools (CARD-218 / CARD-233).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Optional, Sequence

from src.application.orchestration.job_phase_memory import (
    JobPhaseMemoryBridge,
    persist_phase_memory_for_job,
)

logger = logging.getLogger(__name__)

# Minimum matched capability IDs to skip research [REQ-RESEARCH-001/002].
SUFFICIENT_MATCH_MIN = 2

# Critical capability families implied by success_rule keywords.
_CRITICAL_FAMILIES: dict[str, frozenset[str]] = {
    "health": frozenset({"health", "probe", "http", "200", "uptime", "endpoint"}),
    "verify": frozenset({"pytest", "test", "verify", "assert", "checker", "passes"}),
    "wiki": frozenset({"wiki", "notes", "search", "inventory", "document", "index"}),
    "execute": frozenset({"execute", "run", "apply", "deploy", "ship"}),
}

_TOKEN_RE = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def _tokenize(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN_RE.findall(text or "") if t}


@dataclass(frozen=True)
class CatalogMatchAssessment:
    """Deterministic thin/gap vs sufficient result [CARD-231 heuristic]."""

    sufficient: bool
    research_inserted: bool
    reason: str
    match_count: int
    missing_families: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "sufficient": self.sufficient,
            "research_inserted": self.research_inserted,
            "reason": self.reason,
            "match_count": self.match_count,
            "missing_families": list(self.missing_families),
            "sufficient_match_min": SUFFICIENT_MATCH_MIN,
        }


def implied_critical_families(success_rule: str) -> tuple[str, ...]:
    """Which critical families the success_rule / stop condition implies."""
    tokens = _tokenize(success_rule or "")
    rule_l = (success_rule or "").lower()
    found: list[str] = []
    for family, kws in _CRITICAL_FAMILIES.items():
        if tokens & kws or any(k in rule_l for k in kws):
            found.append(family)
    return tuple(found)


def _matched_keyword_universe(
    matched_ids: Sequence[str],
    matched_entry_keywords: Optional[Mapping[str, Sequence[str]]],
) -> set[str]:
    have: set[str] = set()
    for mid in matched_ids:
        sid = str(mid)
        have |= _tokenize(sid.replace(".", " ").replace("-", " ").replace("_", " "))
        if matched_entry_keywords and sid in matched_entry_keywords:
            for kw in matched_entry_keywords[sid] or []:
                have |= _tokenize(str(kw))
    return have


def assess_catalog_match(
    matched_ids: Sequence[str] | None,
    success_rule: str | None,
    *,
    matched_entry_keywords: Optional[Mapping[str, Sequence[str]]] = None,
) -> CatalogMatchAssessment:
    """
    Thin/gap vs sufficient heuristic [REQ-RESEARCH-001/002] [CARD-257].

    thin when:
      - empty matched IDs
      - match count below SUFFICIENT_MATCH_MIN AND outcome not covered
      - success_rule implies critical family with no keyword overlap on matches
    sufficient when:
      - matched tools cover all implied critical families (even if count < MIN)
        → reason outcome_covered_by_matched [REQ-RGATE-001]
      - otherwise count >= MIN and critical families covered or none implied
    """
    ids = [str(x).strip() for x in (matched_ids or []) if str(x).strip()]
    rule = (success_rule or "").strip()
    count = len(ids)

    if count == 0:
        return CatalogMatchAssessment(
            sufficient=False,
            research_inserted=True,
            reason="empty_matched_ids",
            match_count=0,
            missing_families=("all",),
        )

    # CARD-257 / REQ-RGATE-001: if matched tools already cover every critical
    # family the success_rule implies, skip Research even when count < MIN.
    # Never hard-fail the Job on thin match alone when outcome is covered.
    needed = implied_critical_families(rule)
    if needed:
        have = _matched_keyword_universe(ids, matched_entry_keywords)
        missing = tuple(
            fam for fam in needed if not (have & _CRITICAL_FAMILIES[fam])
        )
        if not missing:
            return CatalogMatchAssessment(
                sufficient=True,
                research_inserted=False,
                reason="outcome_covered_by_matched",
                match_count=count,
                missing_families=(),
            )
        if count >= SUFFICIENT_MATCH_MIN:
            return CatalogMatchAssessment(
                sufficient=False,
                research_inserted=True,
                reason="missing_critical_roles:" + ",".join(missing),
                match_count=count,
                missing_families=missing,
            )

    if count < SUFFICIENT_MATCH_MIN:
        return CatalogMatchAssessment(
            sufficient=False,
            research_inserted=True,
            reason=f"below_threshold:{count}<{SUFFICIENT_MATCH_MIN}",
            match_count=count,
            missing_families=(),
        )

    return CatalogMatchAssessment(
        sufficient=True,
        research_inserted=False,
        reason="sufficient_match",
        match_count=count,
        missing_families=(),
    )


def build_research_facts(
    *,
    intent: str,
    success_rule: str,
    matched_capability_ids: Sequence[str],
    assessment: CatalogMatchAssessment,
) -> list[str]:
    """Facts written into memory.db for the research phase."""
    ids = [str(x) for x in (matched_capability_ids or []) if str(x).strip()]
    facts = [
        f"research_before_plan: reason={assessment.reason}",
        f"research_before_plan: match_count={assessment.match_count}",
        f"research_before_plan: matched_ids={ids or ['(none)']}",
        f"research_before_plan: success_rule={success_rule.strip()[:240]}",
    ]
    if assessment.missing_families:
        facts.append(
            "research_before_plan: missing_families="
            + ",".join(assessment.missing_families)
        )
    compact = re.sub(r"\s+", " ", (intent or "").strip())
    if compact:
        facts.append(f"research_before_plan: intent={compact[:240]}")
    return facts


def propose_catalog_gaps(
    *,
    assessment: CatalogMatchAssessment,
    success_rule: str,
    matched_capability_ids: Sequence[str],
) -> list[dict[str, Any]]:
    """
    Propose catalog gaps for later scaffold (CARD-218/233).

    Returns proposal dicts only — never writes trusted skills/tools.
    """
    proposals: list[dict[str, Any]] = []
    if assessment.reason == "empty_matched_ids":
        proposals.append(
            {
                "kind": "catalog_gap",
                "gap": "no_matched_capabilities",
                "suggested_action": "draft_candidate_via_scaffold_spine",
                "success_rule": (success_rule or "")[:240],
                "trust_write_forbidden": True,
            }
        )
    for fam in assessment.missing_families:
        if fam == "all":
            continue
        proposals.append(
            {
                "kind": "catalog_gap",
                "gap": f"missing_critical_role:{fam}",
                "family": fam,
                "keywords": sorted(_CRITICAL_FAMILIES.get(fam, ())),
                "suggested_action": "draft_candidate_via_scaffold_spine",
                "matched_capability_ids": list(matched_capability_ids or []),
                "trust_write_forbidden": True,
            }
        )
    if assessment.reason.startswith("below_threshold"):
        proposals.append(
            {
                "kind": "catalog_gap",
                "gap": "below_match_threshold",
                "reason": assessment.reason,
                "sufficient_match_min": SUFFICIENT_MATCH_MIN,
                "match_count": assessment.match_count,
                "suggested_action": "expand_catalog_or_enrich_keywords",
                "trust_write_forbidden": True,
            }
        )
    return proposals


def run_standing_research(
    orch: Any,
    *,
    job_id: str,
    intent: str,
    success_rule: str,
    matched_capability_ids: Sequence[str],
    assessment: CatalogMatchAssessment,
    trusted_skill_writer: Optional[Callable[..., Any]] = None,
    trusted_tool_writer: Optional[Callable[..., Any]] = None,
    data_dir: Optional[str] = None,
) -> dict[str, Any]:
    """
    Execute research-before-plan side effects [REQ-RESEARCH-003/004].

    Writes memory.db facts + gap proposals. Deliberately does not call
    trusted_skill_writer / trusted_tool_writer even if provided.
    """
    _ = trusted_skill_writer
    _ = trusted_tool_writer  # never invoked — 218/233 out of scope

    facts = build_research_facts(
        intent=intent,
        success_rule=success_rule,
        matched_capability_ids=matched_capability_ids,
        assessment=assessment,
    )
    proposals = propose_catalog_gaps(
        assessment=assessment,
        success_rule=success_rule,
        matched_capability_ids=matched_capability_ids,
    )
    for p in proposals:
        facts.append(f"catalog_gap_proposal: {p.get('gap')}")

    agent_id = "assistant"
    phase_index = 0
    phase_name = "Research"
    try:
        job = orch._store.get_job(job_id)  # noqa: SLF001 — standing path helper
        agent_id = getattr(job, "agent_id", None) or agent_id
        phases = orch._store.list_phases_for_job(job_id)  # noqa: SLF001
        research = next(
            (p for p in phases if str(p.name or "").lower().startswith("research")),
            phases[0] if phases else None,
        )
        if research is not None:
            phase_index = int(getattr(research, "index", 0) or 0)
            phase_name = str(research.name or "Research")
    except Exception as exc:  # noqa: BLE001
        logger.debug("research job lookup soft-fail: %s", exc)

    dd = data_dir if data_dir is not None else getattr(orch, "_data_dir", None)
    fact_ids = persist_phase_memory_for_job(
        agent_id=str(agent_id),
        job_id=job_id,
        phase_index=phase_index,
        phase_name=phase_name,
        facts=facts,
        data_dir=dd,
    )

    # Stamp memory refs onto checkpoint when possible.
    try:
        phases = orch._store.list_phases_for_job(job_id)  # noqa: SLF001
        research = next(
            (p for p in phases if str(p.name or "").lower().startswith("research")),
            phases[0] if phases else None,
        )
        if research is not None and hasattr(orch, "_commit_checkpoint"):
            orch._commit_checkpoint(  # noqa: SLF001
                research,
                verifier_status="none",
                hitl_park_state=False,
                matched_capability_ids=list(matched_capability_ids or []),
                memory_fact_ids=fact_ids,
                research_inserted=True,
                research_reason=assessment.reason,
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("research checkpoint stamp soft-fail: %s", exc)

    # Standing journey research span/event [REQ-RESEARCH-004].
    ev = getattr(getattr(orch, "_store", None), "save_standing_journey_event", None)
    if callable(ev):
        try:
            ev(
                job_id=job_id,
                kind="research",
                payload={
                    "research_inserted": True,
                    "reason": assessment.reason,
                    "match_count": assessment.match_count,
                    "missing_families": list(assessment.missing_families),
                    "catalog_gap_proposals": proposals,
                    "memory_fact_ids": list(fact_ids),
                    "trust_write_forbidden": True,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("research journey event soft-fail: %s", exc)

    return {
        "ok": True,
        "job_id": job_id,
        "research_inserted": True,
        "reason": assessment.reason,
        "memory_fact_ids": list(fact_ids),
        "catalog_gap_proposals": proposals,
        "trusted_writes": False,
    }


__all__ = [
    "SUFFICIENT_MATCH_MIN",
    "CatalogMatchAssessment",
    "assess_catalog_match",
    "auto_complete_prepared_research",
    "build_research_facts",
    "format_job_failed_honesty",
    "implied_critical_families",
    "is_research_phase",
    "propose_catalog_gaps",
    "research_already_prepared",
    "run_standing_research",
    "JobPhaseMemoryBridge",
]


def is_research_phase(phase: Any) -> bool:
    return str(getattr(phase, "name", "") or "").lower().startswith("research")


def research_already_prepared(orch: Any, job_id: str) -> bool:
    """True when mint already ran run_standing_research side-effects [CARD-257]."""
    getter = getattr(orch, "get_latest_checkpoint", None)
    if not callable(getter):
        return False
    try:
        cp = getter(job_id)
    except Exception:
        return False
    return bool(cp is not None and getattr(cp, "research_inserted", False))


def auto_complete_prepared_research(orch: Any, phase: Any, job: Any) -> dict[str, Any]:
    """
    Complete Research without LLM when side-effects already ran [REQ-RGATE-002].

    CARD-231 inserts Research for thin/gap; CARD-257 forbids fail-closed kill via
    Research LLM timeout. memory.db facts + gap proposals were written at mint.
    """
    from src.domain.orchestration.models import HandoffPacket

    reason = ""
    getter = getattr(orch, "get_latest_checkpoint", None)
    if callable(getter):
        try:
            cp = getter(getattr(job, "id", None) or "")
            reason = str(getattr(cp, "research_reason", "") or "") if cp is not None else ""
        except Exception:
            reason = ""
    facts = [
        "research_auto_completed: side_effects_at_mint",
        f"research_reason: {reason or 'unknown'}",
        "research_llm_skipped: true",
    ]
    packet = HandoffPacket(
        goal=getattr(phase, "success_rule", None) or "Research",
        facts=facts,
        constraints=[],
        done_when=getattr(phase, "success_rule", None) or "Research complete",
        budget={},
    )
    orch.complete_phase(phase.id, packet, advance=True)
    return {
        "ok": True,
        "research_auto_completed": True,
        "reason": reason or "unknown",
        "job_id": getattr(job, "id", None),
        "phase_id": getattr(phase, "id", None),
    }


def format_job_failed_honesty(
    *,
    job_id: str,
    phase_name: str | None,
    reason: str,
) -> str:
    """Status-honest assistant claim when Journey/job is FAILED [REQ-RGATE-003]."""
    phase_bit = f" during {phase_name}" if phase_name else ""
    detail = (reason or "phase failed").strip()
    return (
        f"Job {job_id} FAILED{phase_bit}: {detail}. "
        "Not done — Journey shows FAILED; no deliverable claimed."
    )

