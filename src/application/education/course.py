"""Education Learning OS Course + Mastery pipeline [CARD-320].

Durable course in agent *_memory.db (education_course). Course pipeline is the
DEFAULT Ask path; mode-picker is secondary jump-to-step only. Mastery gate is
binary external only (grade_answer_binary). No Dual Coding chrome on this card.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from src.application.education.elaboration import (
    build_elaboration_note_content,
)
from src.application.education.labs import (
    build_lab_note_content,
    grade_lab_submission,
)
from src.application.education.quiz_engine import grade_answer_binary

COURSE_KIND = "education_course"

# Ordered Learning OS default pipeline (CARD-320 baseline).
DEFAULT_COURSE_STEPS: tuple[str, ...] = (
    "priming",
    "retrieval",
    "elaboration",
    "construction",
    "application",
    "analysis",
    "environment",
    "retention",
)

# Ordered Learning OS pipeline with Dual Coding as an ordered step [CARD-321].
ORDERED_COURSE_STEPS: tuple[str, ...] = (
    "priming",
    "dual_coding",
    "retrieval",
    "elaboration",
    "construction",
    "application",
    "analysis",
    "environment",
    "retention",
)

# Steps that no longer exist. Courses stored before their removal may still list them; they are skipped
# without writing anything. "amplifiers" wrote filler wiki notes and filler quiz items [CARD-639].
RETIRED_COURSE_STEPS: frozenset[str] = frozenset({"amplifiers"})


def _live_steps(steps: Sequence[str]) -> List[str]:
    """Step names with blanks and retired steps removed [CARD-639]."""
    return [str(s).strip() for s in steps if str(s).strip() and str(s).strip() not in RETIRED_COURSE_STEPS]


# Steps allowed via mode-picker jump (includes all ordered steps + custom).
JUMPABLE_STEPS: frozenset[str] = frozenset(
    list(ORDERED_COURSE_STEPS) + ["custom"]
)


def is_course_pipeline_default() -> bool:
    """Course pipeline is the DEFAULT Studio path (mode-picker = jump-to-step)."""
    return True


def _normalize_topic(topic_id: str) -> str:
    return (topic_id or "").strip()


def start_or_resume_course(
    memory_repo: Any,
    *,
    topic_id: str,
    steps: Optional[Sequence[str]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Start a durable course or resume the active one for topic_id."""
    topic = _normalize_topic(topic_id)
    if not topic:
        raise ValueError("topic_id required")
    step_list = _live_steps(steps or DEFAULT_COURSE_STEPS)
    if not step_list:
        step_list = list(DEFAULT_COURSE_STEPS)

    existing = memory_repo.get_education_course_by_topic(topic, prefer_active=True)
    if existing and existing.get("status") == "active":
        return existing

    latest = memory_repo.get_education_course_by_topic(topic, prefer_active=False)
    if latest and latest.get("status") != "completed":
        if latest.get("status") != "active":
            return memory_repo.update_education_course_step(
                course_id=latest["course_id"],
                current_step=latest["current_step"],
                status="active",
                now=now,
            )
        return latest

    course_id = memory_repo.upsert_education_course(
        topic_id=topic,
        steps=step_list,
        current_step=step_list[0],
        status="active",
        now=now,
    )
    row = memory_repo.get_education_course(course_id)
    assert row is not None
    return row


def get_course(memory_repo: Any, *, course_id: str) -> Optional[Dict[str, Any]]:
    return memory_repo.get_education_course(course_id)


def jump_to_course_step(
    memory_repo: Any,
    *,
    course_id: str,
    step: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Secondary mode-picker: jump current_step without inventing a new course."""
    course = memory_repo.get_education_course(course_id)
    if not course:
        raise KeyError(f"education course not found: {course_id}")
    target = (step or "").strip().lower()
    if not target:
        raise ValueError("step required")
    if target in RETIRED_COURSE_STEPS:
        raise ValueError(f"course step removed: {target}")
    steps = list(course.get("steps") or DEFAULT_COURSE_STEPS)
    if target not in JUMPABLE_STEPS and target not in steps:
        raise ValueError(f"unknown course step: {target}")
    status = "active" if course.get("status") != "completed" else course.get("status")
    return memory_repo.update_education_course_step(
        course_id=course_id,
        current_step=target,
        status=status,
        now=now,
    )


def _next_step(steps: Sequence[str], current: str) -> Optional[str]:
    """Next step after current, skipping retired steps a stored course may still list [CARD-639]."""
    cur = (current or "").strip()
    ordered = [str(s).strip() for s in steps if str(s).strip()]
    live = _live_steps(ordered)
    if cur not in ordered:
        return live[0] if live else None
    for candidate in ordered[ordered.index(cur) + 1:]:
        if candidate not in RETIRED_COURSE_STEPS:
            return candidate
    return None


def _nothing_written(
    step_name: str, reason: str, knowledge_type: Optional[str] = None, detail: str = ""
) -> Dict[str, Any]:
    """A completed step that writes no wiki note, quiz item or memory fact, with the reason [CARD-640]."""
    return {
        "success": True,
        "step": step_name,
        "wiki_path": None,
        "artifact": {},
        "ledger": {"success": True, "count": 0, "item_ids": []},
        "item_ids": [],
        "tools_used": [],
        "knowledge_type": knowledge_type,
        "skip_reason": reason,
        "skip_detail": detail or "",  # which check refused the model's reply [CARD-653]
    }


def _course_note_meta(step_name: str, topic: str) -> Dict[str, Any]:
    """Front matter for a course step note: its own document type plus kind/step/topic [CARD-645]."""
    return {
        "document_type": f"course_{step_name}",
        "extra_frontmatter": {
            "kind": "education_course_step",
            "step": step_name,
            "course_topic": topic,
        },
    }


def _write_step_artifact(
    *,
    step: str,
    topic: str,
    memory_repo: Any,
    dual_coding: Optional[Dict[str, Any]] = None,
    composed: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Write a completed step, first dropping a quiz question that nearly repeats a ledger item [CARD-650]."""
    from src.application.education.grounded import drop_duplicate_quiz
    from src.application.education.priming_schema import slug_topic

    step_name = (step or "").strip().lower()
    # Re-running a step overwrites its own item, so that one is not a duplicate. Priming items are
    # keyed by note path, so a re-run priming question that repeats the old one is dropped instead.
    own = None if step_name == "priming" else f"course_{slug_topic(_normalize_topic(topic))}_{step_name}"[:48]
    quiz_skip = None
    quiz_dup = None
    # CARD-654: whether the composer asked again because its question repeated an earlier one.
    quiz_retry = next((c.get("quiz_retry") for c in (dual_coding, composed) if (c or {}).get("quiz_retry")), None)
    deduped = []
    for content in (dual_coding, composed):
        out = drop_duplicate_quiz(content, memory_repo, own_item_id=own)
        if out is not content and (out or {}).get("quiz_skip_reason"):
            quiz_skip = out["quiz_skip_reason"]
            quiz_dup = {
                "question": out.get("dropped_question") or "",
                "duplicate_of": (out.get("duplicate_of") or {}).get("prompt") or "",
            }
        deduped.append(out)
    result = _write_step_artifact_body(
        step=step, topic=topic, memory_repo=memory_repo, dual_coding=deduped[0], composed=deduped[1], **kwargs
    )
    result["quiz_skip_reason"] = quiz_skip if result.get("wiki_path") else None
    result["quiz_duplicate"] = quiz_dup if result.get("wiki_path") else None
    result["quiz_retry"] = quiz_retry if result.get("wiki_path") else None
    return result


def _write_step_artifact_body(
    *,
    step: str,
    topic: str,
    wiki_tools_or_store: Any,
    memory_repo: Any,
    teach_style: str = "",
    learner_explanation: Optional[str] = None,
    lab_submission: Optional[str] = None,
    course_id: Optional[str] = None,
    knowledge_type: Optional[str] = None,
    dual_coding: Optional[Dict[str, Any]] = None,
    composed: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Write Wiki artifact + ledger anchors for a completed step that has its own writer.

    Priming, dual coding, elaboration, construction, application, analysis and environment have
    writers. Any other step records progress only and writes nothing [CARD-641].
    """
    from src.application.education.knowledge_types import resolve_step_knowledge_type

    step_name = (step or "").strip().lower()
    topic_clean = _normalize_topic(topic)
    ktype = resolve_step_knowledge_type(step_name, explicit=knowledge_type)

    if step_name == "priming":
        # CARD-646: priming is written only from content grounded in the learner's notes.
        from src.application.education.priming import priming_writeback

        result = priming_writeback(
            topic=topic_clean,
            wiki_tools_or_store=wiki_tools_or_store,
            memory_repo=memory_repo,
            composed=composed,
            now=now,
        )
        if result.get("skipped"):
            return _nothing_written(
                step_name, result.get("skip_reason") or "not_composed", ktype, str(result.get("detail") or "")
            )
        return {
            "success": bool(result.get("success")),
            "step": step_name,
            "wiki_path": result.get("path"),
            "artifact": {
                "path": result.get("path"),
                "kind": result.get("kind") or "priming",
                "title": result.get("title"),
                "sources": result.get("sources") or [],
            },
            "ledger": result.get("ledger") or {},
            "item_ids": list((result.get("ledger") or {}).get("item_ids") or []),
            "tools_used": result.get("tools_used") or [],
            "skip_reason": None,
        }

    from src.application.education.priming_schema import slug_topic
    from src.application.education.priming_wiki_io import create_priming_note
    from src.application.education.templates import get_template_for_step

    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    stamp = base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if step_name == "dual_coding":
        # CARD-640: only content grounded in the learner's own wiki notes is written; otherwise nothing.
        composed = dual_coding or composed or {}
        if not composed.get("ok"):
            return _nothing_written(
                step_name, composed.get("skip_reason") or "not_composed", ktype, str(composed.get("detail") or "")
            )
        title = f"Course Dual Coding: {topic_clean}"
        sources = [s for s in (composed.get("sources") or []) if isinstance(s, dict) and s.get("path")]
        source_links = "\n".join(
            f"- [[{str(s['path'])[:-3] if str(s['path']).endswith('.md') else s['path']}]] {s.get('title') or ''}".rstrip()
            for s in sources
        )
        steps_md = "\n".join(f"- {i}. {s}" for i, s in enumerate(composed.get("steps") or [], start=1))
        content = (
            f"# {title}\n\n"
            f"## Verbal Code\n"
            f"{composed['prose']}\n\n"
            f"## Visual Code\n"
            f"```mermaid\n"
            f"{str(composed['mermaid']).strip()}\n"
            f"```\n\n"
            + (f"## Step-through\n{steps_md}\n\n" if steps_md else "")
            + f"## Sources\n{source_links}\n"
            + (f"\n## Quiz\nQ: {composed['question']}\nA: {composed['answer']}\n" if composed.get("question") else "")
        )
        tpl = get_template_for_step(step_name)
        create_res = create_priming_note(
            wiki_tools_or_store,
            **_course_note_meta(step_name, topic_clean),
            title=title,
            content=content,
            topic=topic_clean,
            tags=["education", "course", "dual_coding"],
            summary=f"Dual coding from your notes on {topic_clean}",
            template=tpl,
        )
        path = str(create_res.get("path") or "")
        note_ok = bool(create_res.get("success")) and (
            bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
        )

        ledger: Dict[str, Any] = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            item_id = f"course_{slug_topic(topic_clean)}_dual_coding"[:48]
            mid = None
            if composed.get("question"):
                mid = memory_repo.upsert_education_mastery(
                    item_id=item_id,
                    topic=topic_clean,
                    wiki_path=path,
                    prompt=str(composed["question"]),
                    expected_answer=str(composed["answer"]),
                    grade="unseen",
                )
            try:
                from src.application.education.learner_model import LEARNER_ENTITY

                memory_repo.add_semantic_fact(
                    entity=LEARNER_ENTITY,
                    attribute="course_step_dual_coding",
                    value=f"{topic_clean}|{path}|{stamp}",
                    category="education_learner",
                    confidence=1.0,
                    decay_half_life_days=90.0,
                    fact_id=f"edu_course_{slug_topic(topic_clean)}_dual_coding"[:64],
                )
            except Exception:
                pass
            ledger = {"success": True, "count": 1 if mid else 0, "item_ids": [mid] if mid else []}

        return {
            "success": note_ok,
            "step": step_name,
            "wiki_path": path,
            "artifact": {
                "path": path,
                "kind": "course_dual_coding",
                "title": title,
                "sources": sources,
            },
            "ledger": ledger,
            "item_ids": list(ledger.get("item_ids") or []),
            "tools_used": ["wiki_note_create"] if note_ok else [],
            "skip_reason": None,
        }

    if step_name == "elaboration":
        # CARD-644: nothing without the learner's explanation; with one, the note holds it, and the
        # follow-ups and quiz item are added only when grounded in what the learner wrote.
        explanation = (learner_explanation or "").strip()
        if not explanation:
            return _nothing_written(step_name, "no_learner_explanation", ktype)
        grounded_elab = composed if (composed or {}).get("ok") else None
        title = f"Course Elaboration: {topic_clean}"
        content = build_elaboration_note_content(
            topic_clean,
            learner_explanation=explanation,
            composed=grounded_elab,
        )
        tpl = get_template_for_step(step_name)
        create_res = create_priming_note(
            wiki_tools_or_store,
            **_course_note_meta(step_name, topic_clean),
            title=title,
            content=content,
            topic=topic_clean,
            tags=["education", "course", "elaboration"],
            summary=f"Your explanation of {topic_clean}",
            template=tpl,
        )
        path = str(create_res.get("path") or "")
        note_ok = bool(create_res.get("success")) and (
            bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
        )

        ledger: Dict[str, Any] = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            ids: List[str] = []
            if grounded_elab and grounded_elab.get("question"):
                ids.append(
                    memory_repo.upsert_education_mastery(
                        item_id=f"course_{slug_topic(topic_clean)}_elaboration"[:48],
                        topic=topic_clean,
                        wiki_path=path,
                        prompt=str(grounded_elab["question"]),
                        expected_answer=str(grounded_elab["answer"]),
                        grade="unseen",
                    )
                )
            try:
                from src.application.education.learner_model import LEARNER_ENTITY

                memory_repo.add_semantic_fact(
                    entity=LEARNER_ENTITY,
                    attribute="course_step_elaboration",
                    value=f"{topic_clean}|{path}|{stamp}|{explanation[:120]}",
                    category="education_learner",
                    confidence=1.0,
                    decay_half_life_days=90.0,
                    fact_id=f"edu_course_{slug_topic(topic_clean)}_elaboration"[:64],
                )
            except Exception:
                pass
            ledger = {"success": True, "count": len(ids), "item_ids": ids}

        return {
            "success": note_ok,
            "step": step_name,
            "wiki_path": path,
            "artifact": {
                "path": path,
                "kind": "course_elaboration",
                "title": title,
                "sources": (grounded_elab or {}).get("sources") or [],
            },
            "ledger": ledger,
            "item_ids": list(ledger.get("item_ids") or []),
            "tools_used": ["wiki_note_create"] if note_ok else [],
            "skip_reason": None,
            # Why follow-ups and the quiz item were left out (the explanation itself is still saved).
            "grounding_skip_reason": None if grounded_elab else ((composed or {}).get("skip_reason") or "not_composed"),
        }
    if step_name in ("construction", "application"):
        # CARD-643: the lab comes only from the learner's notes (grounded spec) and the submission is
        # graded only against that spec's criteria. No template lab, no made-up baseline submission.
        from src.application.education.construction import create_study_artifact_note

        spec = composed if (composed or {}).get("ok") else None
        sub = (lab_submission or "").strip()
        if not spec and not sub:
            return _nothing_written(
                step_name, (composed or {}).get("skip_reason") or "not_composed", ktype, str((composed or {}).get("detail") or "")
            )

        grade_res: Dict[str, Any] = {}
        if spec and sub:
            grade_res = grade_lab_submission(
                topic=topic_clean,
                step=step_name,
                submission=sub,
                expected_invariants=spec.get("criteria"),
                now=now,
            )
        graded = bool(grade_res)
        passed = bool(grade_res.get("passed")) if graded else True
        title = f"Course Lab {step_name.title()}: {topic_clean}"
        content = build_lab_note_content(
            topic=topic_clean,
            step=step_name,
            lab_spec=spec,
            submission=sub or None,
            grade_result=grade_res or None,
            now=now,
        )
        tpl = get_template_for_step(step_name)
        create_res = create_study_artifact_note(
            wiki_tools_or_store,
            **_course_note_meta(step_name, topic_clean),
            title=title,
            content=content,
            topic=topic_clean,
            tags=["education", "course", "lab", step_name],
            summary=f"{step_name.title()} lab on {topic_clean}",
            template=tpl,
        )
        path = str(create_res.get("path") or "")
        note_ok = bool(create_res.get("success")) and (
            bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
        )

        ledger: Dict[str, Any] = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            ids: List[str] = []
            if spec and spec.get("question"):
                ids.append(
                    memory_repo.upsert_education_mastery(
                        item_id=f"course_{slug_topic(topic_clean)}_{step_name}"[:48],
                        topic=topic_clean,
                        wiki_path=path,
                        prompt=str(spec["question"]),
                        expected_answer=str(spec["answer"]),
                        grade="unseen",
                    )
                )
            try:
                from src.application.education.learner_model import LEARNER_ENTITY

                outcome = ("passed" if passed else "failed:weakness") if graded else "ungraded"
                attr_name = f"course_step_{step_name}" if passed else f"course_step_{step_name}_miss"
                memory_repo.add_semantic_fact(
                    entity=LEARNER_ENTITY,
                    attribute=attr_name,
                    value=f"{topic_clean}|{path}|{stamp}|{outcome}",
                    category="education_learner",
                    confidence=1.0,
                    decay_half_life_days=90.0,
                    fact_id=f"edu_course_{slug_topic(topic_clean)}_{step_name}_{'pass' if passed else 'miss'}"[:64],
                )
            except Exception:
                pass
            ledger = {
                "success": True,
                "count": len(ids),
                "item_ids": ids,
                "grade": ("pass" if passed else "miss") if graded else None,
            }

        return {
            "success": note_ok and passed,
            "passed": passed,
            "graded": graded,
            "grade_result": grade_res,
            "step": step_name,
            "knowledge_type": ktype,
            "wiki_path": path,
            "artifact": {
                "path": path,
                "kind": f"course_{step_name}",
                "title": title,
                "sources": (spec or {}).get("sources") or [],
            },
            "ledger": ledger,
            "item_ids": list(ledger.get("item_ids") or []),
            "tools_used": ["wiki_note_create"] if note_ok else [],
            "skip_reason": None,
            "grounding_skip_reason": None if spec else ((composed or {}).get("skip_reason") or "not_composed"),
        }

    if step_name == "analysis":
        from src.application.education.analysis import (
            build_analysis_note_content,
            build_analysis_scorecard,
            execute_analysis_retention_handoff,
        )

        scorecard = build_analysis_scorecard(memory_repo, topic=topic_clean)
        title = f"Course Analysis: {topic_clean}"
        content = build_analysis_note_content(
            topic=topic_clean,
            scorecard=scorecard,
            now=now,
        )
        tpl = get_template_for_step(step_name)
        create_res = create_priming_note(
            wiki_tools_or_store,
            **_course_note_meta(step_name, topic_clean),
            title=title,
            content=content,
            topic=topic_clean,
            tags=["education", "course", "analysis", "score"],
            summary=f"Analysis scorecard and metacognitive review for {topic_clean}",
            template=tpl,
        )
        path = str(create_res.get("path") or "")
        note_ok = bool(create_res.get("success")) and (
            bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
        )

        ledger: Dict[str, Any] = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            # CARD-647: no quiz item here. The old one asked for this step's own pass rate, a fact
            # about the app (not the topic) whose answer went stale with the next grade.
            # Execute retention handoff across all mastery items for topic
            handoff_res = execute_analysis_retention_handoff(
                memory_repo,
                topic=topic_clean,
                course_id=course_id,
                now=now,
            )
            try:
                from src.application.education.learner_model import LEARNER_ENTITY

                memory_repo.add_semantic_fact(
                    entity=LEARNER_ENTITY,
                    attribute="course_step_analysis",
                    value=f"{topic_clean}|{path}|{stamp}|pass_rate={scorecard.get('pass_rate', 0)}",
                    category="education_learner",
                    confidence=1.0,
                    decay_half_life_days=90.0,
                    fact_id=f"edu_course_{slug_topic(topic_clean)}_analysis"[:64],
                )
            except Exception:
                pass
            ledger = {
                "success": True,
                "count": 0,
                "item_ids": [],
                "handoff": handoff_res,
            }

        return {
            "success": note_ok,
            "step": step_name,
            "wiki_path": path,
            "artifact": {
                "path": path,
                "kind": "course_analysis",
                "title": title,
            },
            "ledger": ledger,
            "item_ids": list(ledger.get("item_ids") or []),
            "tools_used": ["wiki_note_create"] if note_ok else [],
            "scorecard": scorecard,
        }

    if step_name == "environment":
        # CARD-642: only content about the topic from the learner's notes (plus their real delivery
        # profile); otherwise progress only. No template framing, constraints or profile quiz item.
        from src.application.education.environment import (
            build_environment_note_content,
            get_active_delivery_profile,
        )

        grounded_env = composed if (composed or {}).get("ok") else None
        if not grounded_env:
            return _nothing_written(
                step_name, (composed or {}).get("skip_reason") or "not_composed", ktype, str((composed or {}).get("detail") or "")
            )
        active_profile = get_active_delivery_profile(memory_repo) if memory_repo is not None else {}
        title = f"Course Environment: {topic_clean}"
        content = build_environment_note_content(topic=topic_clean, composed=grounded_env, profile=active_profile or None)
        tpl = get_template_for_step(step_name)
        create_res = create_priming_note(
            wiki_tools_or_store,
            **_course_note_meta(step_name, topic_clean),
            title=title,
            content=content,
            topic=topic_clean,
            tags=["education", "course", "environment"],
            summary=f"Where to practise {topic_clean}, from your notes",
            template=tpl,
        )
        path = str(create_res.get("path") or "")
        note_ok = bool(create_res.get("success")) and (
            bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
        )

        ledger: Dict[str, Any] = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            mid = None
            if grounded_env.get("question"):
                mid = memory_repo.upsert_education_mastery(
                    item_id=f"course_{slug_topic(topic_clean)}_environment"[:48],
                    topic=topic_clean,
                    wiki_path=path,
                    prompt=str(grounded_env["question"]),
                    expected_answer=str(grounded_env["answer"]),
                    grade="unseen",
                )
            try:
                from src.application.education.learner_model import LEARNER_ENTITY

                memory_repo.add_semantic_fact(
                    entity=LEARNER_ENTITY,
                    attribute="course_step_environment",
                    value=f"{topic_clean}|{path}|{stamp}|profile={active_profile.get('id')}",
                    category="education_learner",
                    confidence=1.0,
                    decay_half_life_days=90.0,
                    fact_id=f"edu_course_{slug_topic(topic_clean)}_environment"[:64],
                )
            except Exception:
                pass
            ledger = {"success": True, "count": 1 if mid else 0, "item_ids": [mid] if mid else []}

        return {
            "success": note_ok,
            "step": step_name,
            "wiki_path": path,
            "artifact": {
                "path": path,
                "kind": "course_environment",
                "title": title,
                "sources": grounded_env.get("sources") or [],
            },
            "ledger": ledger,
            "item_ids": list(ledger.get("item_ids") or []),
            "tools_used": ["wiki_note_create"] if note_ok else [],
            "skip_reason": None,
            "profile": active_profile,
        }

    # CARD-641: a step without its own writer records progress only. No wiki note, no quiz or
    # mastery-ledger item and no memory fact (the old generic writer saved filler for all three).
    return _nothing_written(step_name, "no_writer", ktype)


def complete_course_step(
    memory_repo: Any,
    *,
    course_id: str,
    wiki_tools_or_store: Any = None,
    teach_style: str = "",
    learner_explanation: Optional[str] = None,
    lab_submission: Optional[str] = None,
    knowledge_type: Optional[str] = None,
    dual_coding: Optional[Dict[str, Any]] = None,
    composed: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Complete current step: Wiki + ledger anchors, then advance (or mark completed).

    `composed` is the grounded content for the current step from
    `grounded_steps.compose_course_step` [CARD-640, CARD-646] (`dual_coding` is the older name for
    the dual coding step). Without it, steps built from the learner's notes write nothing.
    """
    course = memory_repo.get_education_course(course_id)
    if not course:
        raise KeyError(f"education course not found: {course_id}")

    step = (course.get("current_step") or "").strip()
    topic = course.get("topic_id") or ""
    steps = list(course.get("steps") or DEFAULT_COURSE_STEPS)

    if step in RETIRED_COURSE_STEPS:
        # A stored course sitting on a removed step moves on and writes nothing [CARD-639].
        nxt = _next_step(steps, step)
        updated = memory_repo.update_education_course_step(
            course_id=course_id,
            current_step=nxt or step,
            status="active" if nxt else "completed",
            now=now,
        )
        return {
            "success": True,
            "passed": True,
            "skipped": True,
            "skip_reason": "retired_step",
            "completed_step": step,
            "knowledge_type": None,
            "course": updated,
            "wiki_path": None,
            "artifact": {},
            "ledger": {},
            "item_ids": [],
            "tools_used": [],
            "grade_result": {},
        }

    artifact = _write_step_artifact(
        step=step,
        topic=topic,
        wiki_tools_or_store=wiki_tools_or_store,
        memory_repo=memory_repo,
        teach_style=teach_style,
        learner_explanation=learner_explanation,
        lab_submission=lab_submission,
        course_id=course_id,
        knowledge_type=knowledge_type,
        dual_coding=dual_coding,
        composed=composed,
        now=now,
    )

    if step in ("construction", "application") and not artifact.get("passed", True):
        # Honesty gate: failed lab halts course step advancement
        return {
            "success": False,
            "passed": False,
            "completed_step": step,
            "knowledge_type": artifact.get("knowledge_type"),
            "course": course,
            "wiki_path": artifact.get("wiki_path"),
            "artifact": artifact.get("artifact") or {},
            "ledger": artifact.get("ledger") or {},
            "item_ids": artifact.get("item_ids") or [],
            "tools_used": artifact.get("tools_used") or [],
            "grade_result": artifact.get("grade_result") or {},
            "graded": artifact.get("graded"),
            "grounding_skip_reason": artifact.get("grounding_skip_reason"),
            "quiz_skip_reason": artifact.get("quiz_skip_reason"),
            "quiz_duplicate": artifact.get("quiz_duplicate"),
            "quiz_retry": artifact.get("quiz_retry"),
        }

    nxt = _next_step(steps, step)
    if nxt is None:
        updated = memory_repo.update_education_course_step(
            course_id=course_id,
            current_step=step,
            status="completed",
            now=now,
        )
    else:
        updated = memory_repo.update_education_course_step(
            course_id=course_id,
            current_step=nxt,
            status="active",
            now=now,
        )

    return {
        "success": bool(artifact.get("success")),
        "passed": artifact.get("passed", True),
        "skipped": False,
        "skip_reason": artifact.get("skip_reason"),
        "skip_detail": artifact.get("skip_detail") or "",
        "completed_step": step,
        "knowledge_type": artifact.get("knowledge_type"),
        "course": updated,
        "wiki_path": artifact.get("wiki_path"),
        "artifact": artifact.get("artifact") or {},
        "ledger": artifact.get("ledger") or {},
        "item_ids": artifact.get("item_ids") or [],
        "tools_used": artifact.get("tools_used") or [],
        "grade_result": artifact.get("grade_result") or {},
        "graded": artifact.get("graded"),
        "grounding_skip_reason": artifact.get("grounding_skip_reason"),
        "quiz_skip_reason": artifact.get("quiz_skip_reason"),
        "quiz_duplicate": artifact.get("quiz_duplicate"),
        "quiz_retry": artifact.get("quiz_retry"),
    }


def grade_course_mastery(
    memory_repo: Any,
    *,
    item_id: str,
    answer: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Binary external mastery gate only -- miss uses existing Retention next_due."""
    existing = memory_repo.get_education_mastery(item_id)
    if not existing:
        raise KeyError(f"education mastery item not found: {item_id}")
    expected = (existing.get("expected_answer") or "").strip()
    if not expected:
        raise ValueError(
            "empty expected_answer -- re-seed via Priming/course step before grading"
        )
    correct = grade_answer_binary(expected, answer)
    row = memory_repo.record_education_grade(
        item_id=item_id, correct=correct, now=now
    )
    return {
        "grader": "binary_external",
        "correct": bool(correct),
        "item_id": item_id,
        "item": row,
    }


def course_chrome_snapshot(
    memory_repo: Any,
    *,
    topic_id: str = "",
    course_id: str = "",
    mastery_limit: int = 20,
) -> Dict[str, Any]:
    """UI chrome: topic -> ordered steps -> current step -> mastery from ledger."""
    course: Optional[Dict[str, Any]] = None
    if course_id:
        course = memory_repo.get_education_course(course_id)
    elif topic_id:
        course = memory_repo.get_education_course_by_topic(topic_id, prefer_active=True)
        if not course:
            course = memory_repo.get_education_course_by_topic(
                topic_id, prefer_active=False
            )

    mastery: List[Dict[str, Any]] = []
    if hasattr(memory_repo, "list_education_mastery"):
        rows = memory_repo.list_education_mastery(limit=mastery_limit)
        if course:
            topic = course.get("topic_id") or ""
            mastery = [r for r in rows if (r.get("topic") or "") == topic][:mastery_limit]
        else:
            mastery = list(rows)[:mastery_limit]

    resolved_topic = (course or {}).get("topic_id") or topic_id or ""
    depth_data: Optional[Dict[str, Any]] = None
    if resolved_topic and memory_repo is not None:
        from src.application.education.depth import calculate_topic_depth

        depth_data = calculate_topic_depth(memory_repo, topic=resolved_topic)

    delivery_profile_data: Optional[Dict[str, Any]] = None
    if memory_repo is not None:
        from src.application.education.environment import get_active_delivery_profile

        delivery_profile_data = get_active_delivery_profile(memory_repo)

    cur_step = (course or {}).get("current_step") or DEFAULT_COURSE_STEPS[0]
    from src.application.education.knowledge_types import (
        VALID_KNOWLEDGE_TYPES,
        resolve_step_knowledge_type,
    )

    ktype = resolve_step_knowledge_type(cur_step)

    return {
        "kind": COURSE_KIND,
        "pipeline_default": is_course_pipeline_default(),
        "default_steps": list(DEFAULT_COURSE_STEPS),
        "course": course,
        "topic": resolved_topic,
        "steps": _live_steps((course or {}).get("steps") or DEFAULT_COURSE_STEPS),
        "current_step": cur_step,
        "knowledge_type": ktype,
        "available_knowledge_types": list(VALID_KNOWLEDGE_TYPES),
        "status": (course or {}).get("status") or "none",
        "mastery": mastery,
        "depth": depth_data,
        "delivery_profile": delivery_profile_data,
    }

