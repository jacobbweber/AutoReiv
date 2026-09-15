"""Education Learning OS Adaptive Depth & Growth Portfolio [CARD-327].

Calculates topic mastery depth along an adaptive difficulty ladder (Explorer->Foundational->
Practitioner->Expert->Master), anchors depth in memory.db, and generates durable
growth portfolio Wiki notes using the education-portfolio template in 00_Inbox/.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.education.priming_schema import slug_topic
from src.application.education.priming_wiki_io import create_priming_note

DEPTH_ENTITY = "education_depth"
DEPTH_CATEGORY = "education_depth"
DEPTH_ATTRIBUTE = "topic_mastery_depth"

DEPTH_LADDER: list[Dict[str, Any]] = [
    {
        "level": 0,
        "name": "explorer",
        "label": "Explorer",
        "academic_rank": "Kindergarten",
        "description": "Initial concept exposure, priming, and foundational inquiry.",
        "min_items": 0,
        "min_pass_rate": 0.0,
        "next_milestone": "Complete 3 practice items with >= 50% pass rate",
    },
    {
        "level": 1,
        "name": "foundational",
        "label": "Foundational",
        "academic_rank": "Elementary",
        "description": "Core definitions, dual coding models, and recall retention.",
        "min_items": 3,
        "min_pass_rate": 50.0,
        "next_milestone": "Reach 6 items with >= 70% pass rate and complete elaboration",
    },
    {
        "level": 2,
        "name": "practitioner",
        "label": "Practitioner",
        "academic_rank": "High School",
        "description": "Feynman elaboration, construction exercises, and active error awareness.",
        "min_items": 6,
        "min_pass_rate": 70.0,
        "next_milestone": "Reach 10 items with >= 80% pass rate and pass an application lab",
    },
    {
        "level": 3,
        "name": "expert",
        "label": "Expert",
        "academic_rank": "Undergraduate",
        "description": "Rigorous application under workload pressure and metacognitive analysis.",
        "min_items": 10,
        "min_pass_rate": 80.0,
        "next_milestone": "Reach 15 items with >= 90% pass rate and zero recurring error patterns",
    },
    {
        "level": 4,
        "name": "master",
        "label": "Master",
        "academic_rank": "Masters",
        "description": "Deep domain mastery, invariant preservation, and proactive retention cadence.",
        "min_items": 15,
        "min_pass_rate": 90.0,
        "next_milestone": "Maintain active spaced repetition schedule",
    },
]


def _iso_now(now: Optional[datetime] = None) -> str:
    base = now or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def calculate_topic_depth(memory_repo: Any, topic: str) -> Dict[str, Any]:
    """Calculate depth level (0..4) and milestone progress from memory.db ledger items."""
    topic_clean = (topic or "").strip()
    items: List[Dict[str, Any]] = []
    if hasattr(memory_repo, "list_education_mastery"):
        try:
            items = list(memory_repo.list_education_mastery(topic=topic_clean, limit=500) or [])
        except TypeError:
            all_items = list(memory_repo.list_education_mastery(limit=500) or [])
            items = [it for it in all_items if (it.get("topic") or "").strip() == topic_clean]

    total = len(items)
    passed_items = [it for it in items if str(it.get("grade") or "").lower() == "pass"]
    missed_items = [
        it
        for it in items
        if str(it.get("grade") or "").lower() == "miss"
        or int(it.get("miss_count") or 0) > 0
    ]
    passed_count = len(passed_items)
    missed_count = len(missed_items)
    pass_rate = round((passed_count / total * 100.0), 1) if total > 0 else 0.0

    # Determine highest matching rung on the ladder
    matched_rung = DEPTH_LADDER[0]
    for rung in reversed(DEPTH_LADDER):
        if total >= rung["min_items"] and pass_rate >= rung["min_pass_rate"]:
            matched_rung = rung
            break

    curr_level = matched_rung["level"]
    # Progress percent towards next level
    if curr_level < len(DEPTH_LADDER) - 1:
        next_rung = DEPTH_LADDER[curr_level + 1]
        items_needed = max(1, next_rung["min_items"] - matched_rung["min_items"])
        items_done = min(items_needed, max(0, total - matched_rung["min_items"]))
        progress_pct = int((items_done / items_needed) * 100)
        next_milestone = next_rung["next_milestone"]
    else:
        progress_pct = 100
        next_milestone = "Mastery achieved — maintain SRS retention cadence."

    return {
        "topic": topic_clean,
        "level": curr_level,
        "name": matched_rung["name"],
        "label": matched_rung["label"],
        "academic_rank": matched_rung["academic_rank"],
        "description": matched_rung["description"],
        "total_items": total,
        "passed_count": passed_count,
        "missed_count": missed_count,
        "pass_rate": pass_rate,
        "progress_percent": progress_pct,
        "next_milestone": next_milestone,
        "ladder": DEPTH_LADDER,
    }


def record_topic_depth(
    memory_repo: Any,
    topic: str,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Calculate and anchor durable depth fact in memory.db."""
    topic_clean = (topic or "").strip()
    depth = calculate_topic_depth(memory_repo, topic=topic_clean)
    stamp = _iso_now(now)

    fact_id = f"edu_depth_{slug_topic(topic_clean)}"[:64]
    fact_val = (
        f"topic_mastery_depth topic={topic_clean} level={depth['level']} "
        f"name={depth['name']} rank={depth['academic_rank']} "
        f"pass_rate={depth['pass_rate']}% total={depth['total_items']} at={stamp}"
    )

    try:
        if hasattr(memory_repo, "get_semantic_fact") and memory_repo.get_semantic_fact(fact_id):
            with memory_repo.get_connection() as conn:
                conn.execute(
                    "UPDATE semantic_facts SET is_active = 1, value = ?, updated_at = ? WHERE id = ?",
                    (fact_val, stamp, fact_id),
                )
        else:
            memory_repo.add_semantic_fact(
                entity=DEPTH_ENTITY,
                attribute=DEPTH_ATTRIBUTE,
                value=fact_val,
                category=DEPTH_CATEGORY,
                confidence=1.0,
                decay_half_life_days=365.0,
                fact_id=fact_id,
            )
    except Exception:
        pass

    return depth


def get_topic_depth(memory_repo: Any, topic: str) -> Dict[str, Any]:
    """Retrieve depth for topic from cached fact or calculate fresh from ledger."""
    topic_clean = (topic or "").strip()
    fact_id = f"edu_depth_{slug_topic(topic_clean)}"[:64]
    fact = None
    if hasattr(memory_repo, "get_semantic_fact"):
        try:
            fact = memory_repo.get_semantic_fact(fact_id)
        except Exception:
            fact = None

    if fact and int(fact.get("is_active") or 0) == 1:
        val = str(fact.get("value") or "")
        m_level = re.search(r"\blevel=(\d+)", val)
        if m_level:
            lvl = int(m_level.group(1))
            lvl = min(max(0, lvl), len(DEPTH_LADDER) - 1)
            rung = DEPTH_LADDER[lvl]
            m_total = re.search(r"\btotal=(\d+)", val)
            m_rate = re.search(r"\bpass_rate=([0-9.]+)%", val)
            total = int(m_total.group(1)) if m_total else 0
            rate = float(m_rate.group(1)) if m_rate else 0.0
            return {
                "topic": topic_clean,
                "level": lvl,
                "name": rung["name"],
                "label": rung["label"],
                "academic_rank": rung["academic_rank"],
                "description": rung["description"],
                "total_items": total,
                "passed_count": int(total * (rate / 100.0)),
                "missed_count": max(0, total - int(total * (rate / 100.0))),
                "pass_rate": rate,
                "progress_percent": 100 if lvl == 4 else int((lvl / 4) * 100),
                "next_milestone": rung["next_milestone"],
                "ladder": DEPTH_LADDER,
            }

    return calculate_topic_depth(memory_repo, topic=topic_clean)


def build_portfolio_note_content(
    topic: str,
    depth: Dict[str, Any],
    course: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None,
) -> str:
    """Format markdown for Growth Portfolio Wiki note matching education-portfolio template."""
    topic_clean = (topic or "Untitled Topic").strip()
    stamp = _iso_now(now)
    level = depth.get("level", 0)
    label = depth.get("label", "Explorer")
    rank = depth.get("academic_rank", "Kindergarten")
    total = depth.get("total_items", 0)
    passed = depth.get("passed_count", 0)
    missed = depth.get("missed_count", 0)
    pass_rate = depth.get("pass_rate", 0.0)
    progress = depth.get("progress_percent", 0)
    milestone = depth.get("next_milestone", "")
    current_step = (course or {}).get("current_step", "course_active")

    return (
        f"# Growth Portfolio: {topic_clean}\n\n"
        f"> **Topic:** {topic_clean}\n"
        f"> **Pedagogy Phase:** Growth Portfolio & Adaptive Depth\n"
        f"> **Mastery Level:** Level {level} — {label} ({rank})\n"
        f"> **Course Step:** {current_step}\n"
        f"> **Generated:** {stamp}\n\n"
        f"---\n\n"
        f"## 1. Mastery Level & Academic Ladder\n"
        f"- **Level Index:** {level} of 4\n"
        f"- **Academic Rank:** {rank}\n"
        f"- **Designation:** {label}\n"
        f"- **Progress to Next Rung:** {progress}%\n"
        f"- **Target Milestone:** {milestone}\n\n"
        f"## 2. Mastery Statistics & Receipts\n"
        f"- **Total Ledger Items:** {total}\n"
        f"- **Passed Items:** {passed}\n"
        f"- **Missed / Review Items:** {missed}\n"
        f"- **Pass Rate:** {pass_rate}%\n\n"
        f"## 3. Milestones & Growth Trajectory\n"
        f"### Current Cognitive Capabilities\n"
        f"- Verified definitions and mental models for {topic_clean}.\n"
        f"- Grounded with dual coding, retrieval practice, and active invariants.\n"
        f"- Ledger items tracked under single-brain assistant_memory.db.\n\n"
        f"### Next Growth Action\n"
        f"- {milestone}\n"
        f"- Continue through active course pipeline and scheduled routine retention.\n"
    )


def create_growth_portfolio_note(
    wiki_tools_or_store: Any,
    memory_repo: Any,
    topic: str,
    course_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Create and file a growth portfolio note in 00_Inbox/ and anchor facts in memory.db."""
    topic_clean = (topic or "").strip()
    depth = record_topic_depth(memory_repo, topic=topic_clean, now=now)
    stamp = _iso_now(now)

    course = None
    if course_id and hasattr(memory_repo, "get_education_course"):
        course = memory_repo.get_education_course(course_id)

    title = f"Growth Portfolio: {topic_clean}"
    content = build_portfolio_note_content(topic_clean, depth, course=course, now=now)

    create_res = create_priming_note(
        wiki_tools_or_store,
        title=title,
        content=content,
        topic=topic_clean,
        tags=["education", "course", "portfolio", "growth"],
        summary=f"Growth portfolio and adaptive mastery trajectory for {topic_clean}",
        template="education-portfolio",
    )

    path = str(create_res.get("path") or "")
    note_ok = bool(create_res.get("success")) and (
        bool(create_res.get("inbox")) or path.replace("\\", "/").startswith("00_Inbox/")
    )

    if note_ok and memory_repo is not None:
        item_id = f"course_{slug_topic(topic_clean)}_portfolio"[:48]
        prompt = f"What is the current growth portfolio depth level for {topic_clean}?"
        expected = f"Level {depth['level']} ({depth['label']}, {depth['academic_rank']})"
        memory_repo.upsert_education_mastery(
            item_id=item_id,
            topic=topic_clean,
            wiki_path=path,
            prompt=prompt,
            expected_answer=expected,
            grade="pass",
        )
        try:
            from src.application.education.learner_model import LEARNER_ENTITY

            memory_repo.add_semantic_fact(
                entity=LEARNER_ENTITY,
                attribute="course_growth_portfolio",
                value=f"{topic_clean}|{path}|level={depth['level']}|rank={depth['academic_rank']}|at={stamp}",
                category="education_learner",
                confidence=1.0,
                decay_half_life_days=365.0,
                fact_id=f"edu_portfolio_{slug_topic(topic_clean)}"[:64],
            )
        except Exception:
            pass

    return {
        "success": note_ok,
        "path": path,
        "topic": topic_clean,
        "depth": depth,
        "note_title": title,
    }
