"""Unit tests for CARD-334: Education knowledge-type anchors.

Tests:
1. Four distinct knowledge types (concept, tool, method, problem) with unique artifact shapes.
2. Template catalog contains templates for all 4 knowledge types.
3. Step-to-knowledge-type resolution with defaults and explicit overrides.
4. (Template artifact builder removed in CARD-652.)
5. Course chrome snapshot includes knowledge_type and available_knowledge_types.
6. Course step completion persists knowledge-type front matter and memory anchors.
7. Remains separate from CARD-324 Construction/Application graded lab pressure.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.application.education.course import (
    complete_course_step,
    course_chrome_snapshot,
)
from src.application.education.knowledge_types import (
    KNOWLEDGE_SHAPES,
    VALID_KNOWLEDGE_TYPES,
    resolve_step_knowledge_type,
)
from src.application.education.templates import (
    EDUCATION_TEMPLATES,
    get_education_template,
)


def test_valid_knowledge_types_and_shapes():
    """REQ-EDU-KTYPE-001: concept, tool, method, problem each have distinct shapes."""
    assert set(VALID_KNOWLEDGE_TYPES) == {"concept", "tool", "method", "problem"}
    for ktype in VALID_KNOWLEDGE_TYPES:
        assert ktype in KNOWLEDGE_SHAPES
        shape = KNOWLEDGE_SHAPES[ktype]
        assert "shape_kind" in shape
        assert "label" in shape
        assert "required_sections" in shape
        assert len(shape["required_sections"]) >= 4

    # Verify shapes are distinct
    concept_sections = set(KNOWLEDGE_SHAPES["concept"]["required_sections"])
    tool_sections = set(KNOWLEDGE_SHAPES["tool"]["required_sections"])
    method_sections = set(KNOWLEDGE_SHAPES["method"]["required_sections"])
    problem_sections = set(KNOWLEDGE_SHAPES["problem"]["required_sections"])

    assert concept_sections != tool_sections
    assert concept_sections != method_sections
    assert concept_sections != problem_sections
    assert tool_sections != method_sections
    assert tool_sections != problem_sections
    assert method_sections != problem_sections

    assert "mental_model" in concept_sections
    assert "interface_signature" in tool_sections
    assert "procedure_steps" in method_sections
    assert "symptom_signature" in problem_sections


def test_templates_registered_for_all_knowledge_types():
    """REQ-EDU-KTYPE-001: Wiki templates registered for all 4 knowledge types."""
    for ktype in VALID_KNOWLEDGE_TYPES:
        tpl_id = f"education-{ktype}"
        assert tpl_id in EDUCATION_TEMPLATES
        tpl = get_education_template(tpl_id)
        assert tpl is not None
        assert tpl["slug"] == tpl_id
        assert "tags" in tpl
        assert ktype in tpl["tags"]


def test_step_knowledge_type_resolution():
    """REQ-EDU-KTYPE-002: Steps map to knowledge types with explicit override support."""
    assert resolve_step_knowledge_type("priming") == "concept"
    assert resolve_step_knowledge_type("construction") == "tool"
    assert resolve_step_knowledge_type("elaboration") == "method"
    assert resolve_step_knowledge_type("application") == "problem"

    # Explicit override takes precedence
    assert resolve_step_knowledge_type("priming", explicit="tool") == "tool"
    assert resolve_step_knowledge_type("construction", explicit="problem") == "problem"

    # Invalid override raises ValueError
    with pytest.raises(ValueError):
        resolve_step_knowledge_type("priming", explicit="invalid_unknown")


def test_course_chrome_snapshot_includes_knowledge_type():
    """REQ-EDU-KTYPE-002: Course chrome snapshot surfaces knowledge type for current step."""
    repo = MagicMock()
    repo.get_education_course.return_value = {
        "course_id": "crs_123",
        "topic_id": "Distributed Systems",
        "steps": ["priming", "construction"],
        "current_step": "construction",
        "status": "active",
    }
    repo.list_education_mastery.return_value = []
    repo.get_active_delivery_profile.return_value = {"id": "default", "label": "Standard"}

    chrome = course_chrome_snapshot(repo, course_id="crs_123")
    assert "knowledge_type" in chrome
    assert chrome["knowledge_type"] == "tool"  # construction defaults to tool
    assert "available_knowledge_types" in chrome
    assert set(chrome["available_knowledge_types"]) == {"concept", "tool", "method", "problem"}


def test_complete_course_step_preserves_card324_separation():
    """REQ-EDU-KTYPE-003: Construction/Application labs maintain graded pressure separately."""
    repo = MagicMock()
    repo.get_education_course.return_value = {
        "course_id": "crs_456",
        "topic_id": "Asyncio",
        "steps": ["construction", "application"],
        "current_step": "construction",
        "status": "active",
    }
    repo.upsert_education_mastery.return_value = "mid_1"
    repo.record_education_grade.return_value = {"item_id": "mid_1", "correct": True}
    repo.update_education_course_step.return_value = {
        "course_id": "crs_456",
        "current_step": "application",
        "status": "active",
    }

    tools = MagicMock()
    tools.create_wiki_note.return_value = {"success": True, "path": "00_Inbox/Asyncio.md", "inbox": True}

    res = complete_course_step(
        repo,
        course_id="crs_456",
        wiki_tools_or_store=tools,
        lab_submission="I defined two coroutines and used gather so the event loop awaits both results together.",
        composed={
            "ok": True,
            "objective": "Run two coroutines concurrently on the asyncio event loop",
            "tasks": ["Define two coroutines", "Schedule both with gather", "Await the event loop result"],
            "criteria": ["Uses gather to schedule coroutines", "Awaits results on the event loop"],
            "question": "What schedules several coroutines at once?",
            "answer": "gather",
            "sources": [],
        },
    )

    assert res["success"] is True
    assert res["passed"] is True
    assert res["knowledge_type"] == "tool"
    # Graded lab invariant checking still operates
    assert "grade_result" in res
    assert res["grade_result"].get("passed") is True
