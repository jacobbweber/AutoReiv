"""Course step artifact writers and ledger persistence [CARD-715]."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.education.elaboration import build_elaboration_note_content
from src.application.education.labs import build_lab_note_content, grade_lab_submission


def _normalize_topic(topic_id: str) -> str:
    return (topic_id or "").strip()


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


def _is_inbox_note_ok(create_res: Dict[str, Any], path: str) -> bool:
    return bool(create_res.get("success")) and (
        bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
    )


def _record_learner_step_fact(
    memory_repo: Any,
    *,
    attribute: str,
    value: str,
    fact_id: str,
) -> None:
    try:
        from src.application.education.learner_model import LEARNER_ENTITY

        memory_repo.add_semantic_fact(
            entity=LEARNER_ENTITY,
            attribute=attribute,
            value=value,
            category="education_learner",
            confidence=1.0,
            decay_half_life_days=90.0,
            fact_id=fact_id[:64],
        )
    except Exception:
        pass


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
    own = None if step_name == "priming" else f"course_{slug_topic(_normalize_topic(topic))}_{step_name}"[:48]
    quiz_skip = None
    quiz_dup = None
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
        note_ok = _is_inbox_note_ok(create_res, path)

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
            _record_learner_step_fact(
                memory_repo,
                attribute="course_step_dual_coding",
                value=f"{topic_clean}|{path}|{stamp}",
                fact_id=f"edu_course_{slug_topic(topic_clean)}_dual_coding",
            )
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
        note_ok = _is_inbox_note_ok(create_res, path)

        ledger = {"success": False, "count": 0, "item_ids": []}
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
            _record_learner_step_fact(
                memory_repo,
                attribute="course_step_elaboration",
                value=f"{topic_clean}|{path}|{stamp}|{explanation[:120]}",
                fact_id=f"edu_course_{slug_topic(topic_clean)}_elaboration",
            )
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
            "grounding_skip_reason": None if grounded_elab else ((composed or {}).get("skip_reason") or "not_composed"),
        }

    if step_name in ("construction", "application"):
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
        note_ok = _is_inbox_note_ok(create_res, path)

        ledger = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            ids = []
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
            outcome = ("passed" if passed else "failed:weakness") if graded else "ungraded"
            attr_name = f"course_step_{step_name}" if passed else f"course_step_{step_name}_miss"
            _record_learner_step_fact(
                memory_repo,
                attribute=attr_name,
                value=f"{topic_clean}|{path}|{stamp}|{outcome}",
                fact_id=f"edu_course_{slug_topic(topic_clean)}_{step_name}_{'pass' if passed else 'miss'}",
            )
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
        note_ok = _is_inbox_note_ok(create_res, path)

        ledger = {"success": False, "count": 0, "item_ids": []}
        if note_ok and memory_repo is not None:
            handoff_res = execute_analysis_retention_handoff(
                memory_repo,
                topic=topic_clean,
                course_id=course_id,
                now=now,
            )
            _record_learner_step_fact(
                memory_repo,
                attribute="course_step_analysis",
                value=f"{topic_clean}|{path}|{stamp}|pass_rate={scorecard.get('pass_rate', 0)}",
                fact_id=f"edu_course_{slug_topic(topic_clean)}_analysis",
            )
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
        note_ok = _is_inbox_note_ok(create_res, path)

        ledger = {"success": False, "count": 0, "item_ids": []}
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
            _record_learner_step_fact(
                memory_repo,
                attribute="course_step_environment",
                value=f"{topic_clean}|{path}|{stamp}|profile={active_profile.get('id')}",
                fact_id=f"edu_course_{slug_topic(topic_clean)}_environment",
            )
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

    return _nothing_written(step_name, "no_writer", ktype)
