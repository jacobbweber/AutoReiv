"""Scenario Verify phase: Blueprint capability scenarios as done-whens (CARD-172)."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

from src.application.agent_training_factory.failure_class import (
    classify_failure,
    decide_rinse_outcome,
)
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.registry import (
    PHASE_AUTHOR,
    PHASE_SCENARIO_VERIFY,
)
from src.domain.orchestration.factory_packets import FactoryPacket


def _latest_blueprint(ctx: PhaseContext) -> Dict[str, Any]:
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        return {}
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        payload = getattr(p, "payload", None) or {}
        if role in ("blueprint", "conductor") or getattr(p, "node_id", "") == "blueprint":
            bp = payload.get("blueprint")
            if isinstance(bp, dict):
                return bp
    return {}


def _latest_author_corpus(ctx: PhaseContext) -> Tuple[str, Dict[str, str]]:
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        return "", {}
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        node = getattr(p, "node_id", "") or ""
        if role not in ("author", "coder") and node not in (PHASE_AUTHOR, "coder_node"):
            continue
        payload = getattr(p, "payload", None) or {}
        files_map = payload.get("files_map") or {}
        if not isinstance(files_map, dict):
            continue
        chunks: List[str] = []
        for path, code in files_map.items():
            chunks.append(f"{path}\n{code}")
        return "\n".join(chunks).lower(), dict(files_map)
    return "", {}


def _scenario_list(blueprint: Dict[str, Any], ctx: PhaseContext) -> List[str]:
    raw = blueprint.get("scenarios") or blueprint.get("done_whens") or []
    out: List[str] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                text = str(item.get("text") or item.get("done_when") or item.get("name") or "").strip()
            else:
                text = str(item).strip()
            if text:
                out.append(text)
    if out:
        return out
    # Fallback: distill answers / objectives as done-whens
    try:
        packets = ctx.repo.list_packets(ctx.job_id)
    except Exception:
        packets = []
    for p in reversed(packets or []):
        if getattr(p, "sender_role", "") != "intent_distill":
            continue
        answers = (getattr(p, "payload", None) or {}).get("answers") or {}
        scen = str(answers.get("scenarios") or "").strip()
        if scen:
            parts = re.split(r"\s*\|\s*|\n|;", scen)
            out = [x.strip() for x in parts if x.strip()]
            if out:
                return out
        break
    return [str(o).strip() for o in (ctx.objectives or []) if str(o).strip()]


def _scenario_covered(scenario: str, corpus: str) -> bool:
    """Heuristic coverage: significant tokens from scenario appear in authored corpus."""
    text = (scenario or "").lower()
    if not text or not corpus:
        return False
    if text in corpus:
        return True
    tokens = [t for t in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text) if t not in _STOP]
    if not tokens:
        return False
    hits = sum(1 for t in tokens if t in corpus)
    # Require majority of content tokens
    return hits >= max(2, (len(tokens) + 1) // 2)


_STOP = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "into",
    "via",
    "can",
    "must",
    "should",
    "will",
    "when",
    "done",
    "able",
    "using",
    "a",
    "an",
    "of",
    "to",
    "in",
    "on",
    "or",
    "by",
    "is",
    "are",
    "be",
}


def _persist_rinse_fields(ctx: PhaseContext, **fields: Any) -> None:
    job = ctx.job
    for k, v in fields.items():
        setattr(job, k, v)
    kwargs = {k: v for k, v in fields.items()}
    try:
        ctx.repo.update_job_status(
            job.id,
            job.status if job.status in ("queued", "running") else "running",
            **kwargs,
        )
    except TypeError:
        try:
            ctx.repo.save_job(job)
        except Exception:
            pass
    except Exception:
        try:
            ctx.repo.save_job(job)
        except Exception:
            pass


class ScenarioVerifyPhase:
    id = PHASE_SCENARIO_VERIFY
    label = "Scenario Verify"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        blueprint = _latest_blueprint(ctx)
        scenarios = _scenario_list(blueprint, ctx)
        corpus, files_map = _latest_author_corpus(ctx)

        missing: List[str] = []
        for scen in scenarios:
            if not _scenario_covered(scen, corpus):
                missing.append(scen)

        # No scenarios claimed -> pass through (nothing to prove yet)
        passed = len(missing) == 0
        rinse_count = int(getattr(job, "verify_rinse_count", 0) or 0)
        max_rinses = int(getattr(job, "max_verify_rinses", 3) or 3)
        outer_count = int(getattr(job, "outer_rinse_count", 0) or 0)
        max_outer = int(getattr(job, "max_outer_rinses", 2) or 2)

        if passed:
            message = (
                f"Scenario Verify PASSED ({len(scenarios)} scenario(s) covered)."
                if scenarios
                else "Scenario Verify PASSED (no scenarios claimed)."
            )
            packet = FactoryPacket(
                job_id=job.id,
                packet_type="eval",
                sender_role="scenario_verify",
                recipient_role="verify",
                node_id=PHASE_SCENARIO_VERIFY,
                payload={
                    "message": message,
                    "passed": True,
                    "scenarios": scenarios,
                    "missing_scenarios": [],
                    "phase": PHASE_SCENARIO_VERIFY,
                    "rinse_kind": None,
                },
            )
            ctx.repo.save_packet(packet)
            return PhaseResult(
                outcome="ok",
                message=message,
                artifacts={
                    "passed": True,
                    "scenarios": scenarios,
                    "missing_scenarios": [],
                    "files_map": files_map,
                },
            )

        critic_notes = "Scenario Verify FAILED: missing coverage for: " + "; ".join(missing)
        fclass = classify_failure(critic_notes, scenario_misses=missing)
        outcome = decide_rinse_outcome(
            failure_class=fclass,
            verify_rinse_count=rinse_count,
            max_verify_rinses=max_rinses,
            outer_rinse_count=outer_count,
            max_outer_rinses=max_outer,
        )

        updates: Dict[str, Any] = {"failure_class": fclass}
        rinse_kind = "inner"
        recipient = "author"
        terminal = False
        if outcome == "outer":
            outer_count += 1
            updates["outer_rinse_count"] = outer_count
            rinse_kind = "outer"
            recipient = "intent_distill"
            # Reset inner counter after escalating to outer
            updates["verify_rinse_count"] = 0
            rinse_count = 0
        elif outcome == "fail":
            rinse_count += 1
            updates["verify_rinse_count"] = rinse_count
            rinse_kind = "inner"
            recipient = "author"
        else:  # exhausted
            terminal = True
            if fclass == "sop_how":
                outer_count += 1
                updates["outer_rinse_count"] = outer_count
                rinse_kind = "outer"
            else:
                rinse_count += 1
                updates["verify_rinse_count"] = rinse_count
                rinse_kind = "inner"
            recipient = "orchestrator"

        _persist_rinse_fields(ctx, **updates)

        short = critic_notes if len(critic_notes) <= 180 else critic_notes[:177] + "..."
        if terminal:
            message = (
                f"Scenario Verify FAILED — {rinse_kind} rinse exhausted "
                f"(outer {outer_count}/{max_outer}, inner {rinse_count}/{max_rinses}). "
                f"Reason: {short}"
            )
        elif rinse_kind == "outer":
            message = (
                f"Scenario Verify FAILED — outer rinse ({outer_count}/{max_outer}) "
                f"[{fclass}]. Reason: {short}"
            )
        else:
            message = (
                f"Scenario Verify FAILED — inner rinse ({rinse_count}/{max_rinses}) "
                f"[{fclass}]. Reason: {short}"
            )

        packet = FactoryPacket(
            job_id=job.id,
            packet_type="eval",
            sender_role="scenario_verify",
            recipient_role=recipient,
            node_id=PHASE_SCENARIO_VERIFY,
            payload={
                "message": message,
                "passed": False,
                "scenarios": scenarios,
                "missing_scenarios": missing,
                "critic_notes": critic_notes,
                "failure_class": fclass,
                "rinse_kind": rinse_kind,
                "verify_rinse_count": rinse_count,
                "max_verify_rinses": max_rinses,
                "outer_rinse_count": outer_count,
                "max_outer_rinses": max_outer,
                "terminal_fail": terminal,
                "phase": PHASE_SCENARIO_VERIFY,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome=outcome,
            message=message,
            artifacts={
                "passed": False,
                "missing_scenarios": missing,
                "scenarios": scenarios,
                "critic_notes": critic_notes,
                "failure_class": fclass,
                "rinse_kind": rinse_kind,
                "terminal_fail": terminal,
                "files_map": files_map,
            },
        )
