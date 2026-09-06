"""Intent Distill phase: question battery -> structured intent answers (CARD-172)."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from src.application.agent_training_factory.llm import phase_llm_json
from src.application.agent_training_factory.phase import PhaseContext, PhaseResult
from src.application.agent_training_factory.question_battery import (
    DEFAULT_INTENT_QUESTIONS,
    format_questions_for_prompt,
    implicated_questions,
)
from src.application.agent_training_factory.registry import PHASE_INTENT_DISTILL
from src.application.agent_training_factory.sop_rubric import ensure_structured_sop, sop_is_structured
from src.application.agent_training_factory.wiki_frontmatter import build_factory_frontmatter
from src.domain.orchestration.factory_packets import FactoryPacket

logger = logging.getLogger(__name__)

_sop_is_structured = sop_is_structured


def _latest_failure_blob(ctx: PhaseContext) -> str:
    try:
        packets = ctx.repo.list_packets(ctx.job_id) if ctx.repo else []
    except Exception:
        return ""
    parts: List[str] = []
    for p in reversed(packets or []):
        role = getattr(p, "sender_role", "") or ""
        payload = getattr(p, "payload", None) or {}
        if role not in ("scenario_verify", "verify", "sandbox_runner"):
            continue
        if payload.get("passed") is True:
            continue
        for key in ("critic_notes", "message"):
            val = str(payload.get(key) or "").strip()
            if val:
                parts.append(val)
        misses = payload.get("missing_scenarios") or []
        if isinstance(misses, list):
            parts.extend(str(m) for m in misses if m)
        if parts:
            break
    return "\n".join(parts)


def _heuristic_answers(job: Any, questions: List[Dict], objectives: list) -> Dict[str, str]:
    seed = (getattr(job, "seed_intent", None) or "").strip()
    objs = [str(o) for o in (objectives or []) if str(o).strip()]
    obj_join = "; ".join(objs) if objs else "(none)"
    combined = f"{seed} {obj_join}".lower()
    medium = "cli"
    if any(w in combined for w in ("api", "http", "rest", "endpoint")):
        medium = "api"
    elif any(w in combined for w in ("sql", "database", "postgres", "sqlite")):
        medium = "database"
    elif any(w in combined for w in ("file", "csv", "folder", "filesystem")):
        medium = "filesystem"
    scenarios = objs[:] if objs else [f"Operator achieves: {seed[:120]}" if seed else "Capability works end-to-end"]
    base = {
        "outcome": seed or "Operator completes the trained role task",
        "constraints": "Respect paths/env/credentials from the brief; no secrets in code.",
        "medium": medium,
        "professional_sop": ensure_structured_sop(
            "",
            seed_intent=seed,
            objectives=objs,
            title=str(getattr(job, "target_agent_id", "agent") or "agent"),
        ),
        "official_guidance": "Consult official/standard docs for the target medium and role.",
        "unknowns": "Assumptions marked explicitly; clarify missing paths/credentials before promote.",
        "scenarios": " | ".join(scenarios),
    }
    return {q["id"]: base.get(q["id"], "") for q in questions}


class IntentDistillPhase:
    id = PHASE_INTENT_DISTILL
    label = "Intent Distill"

    async def run(self, ctx: PhaseContext) -> PhaseResult:
        job = ctx.job
        outer = int(getattr(job, "outer_rinse_count", 0) or 0)
        fail_blob = _latest_failure_blob(ctx) if outer > 0 else ""
        questions = implicated_questions(fail_blob) if outer > 0 and fail_blob else list(DEFAULT_INTENT_QUESTIONS)
        objectives = list(ctx.objectives)
        fallback_answers = _heuristic_answers(job, questions, objectives)

        user_bits = [
            f"Agent: {job.target_agent_id}",
            f"Seed intent: {job.seed_intent}",
            f"Objectives: {json.dumps(objectives)}",
            "Answer EACH question id with a concise string. Return ONLY JSON:",
            '{"answers": {"<id>": "..."}, "shape_changed": true|false, "lessons": ["..."]}',
            "Questions:",
            format_questions_for_prompt(questions),
        ]
        if outer > 0 and fail_blob:
            user_bits.insert(
                0,
                "REFLEXION / outer rinse: prior verify failed. Re-answer ONLY the implicated questions "
                f"with failure lessons applied.\nFailure context:\n{fail_blob[:2500]}\n",
            )

        llm_data = await phase_llm_json(
            ctx.gateway,
            system=(
                "You are the Intent Distill phase of the Agent Training Factory. "
                "Produce structured answers to the question battery. Domain-agnostic. "
                "On outer rinse, incorporate Reflexion lessons and set shape_changed if skill/tool shape should change."
            ),
            user="\n".join(user_bits),
            fallback={
                "answers": fallback_answers,
                "shape_changed": outer == 0,
                "lessons": [fail_blob[:500]] if fail_blob else [],
            },
        )

        answers = llm_data.get("answers") if isinstance(llm_data.get("answers"), dict) else {}
        # Ensure every asked question has an answer
        for q in questions:
            qid = q["id"]
            if qid not in answers or not str(answers.get(qid) or "").strip():
                answers[qid] = fallback_answers.get(qid, "")
        shape_changed = bool(llm_data.get("shape_changed")) if outer > 0 else True
        if "shape_changed" not in llm_data and outer > 0:
            # Capability/scenario questions imply possible shape change
            shape_changed = any(q["id"] in ("scenarios", "medium", "professional_sop") for q in questions)

        # Reject vacuous brief-echo SOPs (generic rubric: purpose/steps/verify/rollback).
        sop = str(answers.get("professional_sop") or "")
        answers["professional_sop"] = ensure_structured_sop(
            sop,
            seed_intent=str(job.seed_intent or ""),
            objectives=objectives,
            title=str(job.target_agent_id or "agent"),
        )
        lessons = llm_data.get("lessons") if isinstance(llm_data.get("lessons"), list) else []
        if fail_blob and not lessons:
            lessons = [fail_blob[:500]]

        wiki_paths: List[str] = []
        if ctx.wiki is not None:
            try:
                body = (
                    f"# Intent Distill - {job.target_agent_id}\n\n"
                    + "\n".join(f"## {qid}\n{ans}\n" for qid, ans in answers.items())
                )
                if lessons:
                    body += "\n## Reflexion lessons\n" + "\n".join(f"- {x}" for x in lessons) + "\n"
                fm = build_factory_frontmatter(
                    agent_id=job.target_agent_id,
                    medium=str(answers.get("medium") or "cli"),
                    factory_job_id=job.id,
                    status="intent_distilled",
                    extra={"document_type": "factory-intent-distill"},
                )
                note = ctx.wiki.create_note(
                    title=f"Factory Intent Distill - {job.target_agent_id}",
                    content=body,
                    domain="agent-training-factory",
                    topic=job.target_agent_id,
                    category="notes",
                    document_type="factory-intent-distill",
                    tags=["agent-training-factory", "intent-distill", job.target_agent_id],
                    summary=f"Intent distill answers for {job.target_agent_id}",
                    status="active",
                    extra_meta=fm,
                )
                path = (note or {}).get("path") or (note or {}).get("relative_path") or ""
                if path:
                    wiki_paths.append(path)
            except Exception as exc:
                logger.warning("Intent Distill Wiki write failed: %s", exc)

        # Persist shape_changed hint on job via environment_manifest merge is optional;
        # packet is the SSOT for Ground.
        message = (
            f"Intent Distill completed for {job.target_agent_id} "
            f"({len(questions)} question(s)"
            + (", outer rinse re-ask" if outer > 0 else "")
            + ")."
        )
        packet = FactoryPacket(
            job_id=job.id,
            packet_type="work",
            sender_role="intent_distill",
            recipient_role="ground",
            node_id=PHASE_INTENT_DISTILL,
            payload={
                "message": message,
                "answers": answers,
                "questions_asked": [q["id"] for q in questions],
                "shape_changed": shape_changed,
                "lessons": lessons,
                "wiki_paths": wiki_paths,
                "phase": PHASE_INTENT_DISTILL,
                "rinse_kind": "outer" if outer > 0 else None,
            },
        )
        ctx.repo.save_packet(packet)
        return PhaseResult(
            outcome="ok",
            message=message,
            artifacts={
                "answers": answers,
                "questions_asked": [q["id"] for q in questions],
                "shape_changed": shape_changed,
                "lessons": lessons,
                "wiki_paths": wiki_paths,
            },
        )
