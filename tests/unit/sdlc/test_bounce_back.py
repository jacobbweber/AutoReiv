"""
SDLC bounce-back convention [REQ-SDLC-006, REQ-SDLC-033].
"""

from pathlib import Path

import pytest

from src.application.kernel.tool_registry import _tool_context
from src.application.skills.card_skill import CardSkill

CARD = """# [CARD-300] Bounce

> **Status**: Discuss
> **Created**: 2026-08-29
> **Spec Reference**: `docs/specs/bounce/`
> **Labels**: `type:feature`

---

Body.
"""


@pytest.fixture
def skill(tmp_path: Path) -> CardSkill:
    (tmp_path / ".github" / "cards").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "bounce").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "bounce" / "requirements.md").write_text("# R\n", encoding="utf-8")
    skill = CardSkill(default_project_root=str(tmp_path))
    skill.write_card(content=CARD, filename="CARD-300-bounce.md")
    return skill


def test_returned_below_max_can_resume(skill: CardSkill):
    assert skill.set_card_status(card_id="CARD-300", status="Ready")["success"] is True
    assert skill.set_card_status(card_id="CARD-300", status="In Progress")["success"] is True
    assert skill.set_card_status(card_id="CARD-300", status="In Review")["success"] is True
    ret = skill.set_card_status(card_id="CARD-300", status="Returned", return_reason="gap")
    assert ret["success"] is True
    assert ret["review_rounds"] == 1
    resume = skill.set_card_status(card_id="CARD-300", status="In Progress")
    assert resume["success"] is True
    assert resume["status"] == "In Progress"


def test_returned_at_max_cannot_resume(skill: CardSkill):
    skill.set_card_status(card_id="CARD-300", status="Ready")
    for _ in range(3):
        skill.set_card_status(card_id="CARD-300", status="In Progress")
        skill.set_card_status(card_id="CARD-300", status="In Review")
        skill.set_card_status(card_id="CARD-300", status="Returned", return_reason="gap")
    denied = skill.set_card_status(card_id="CARD-300", status="In Progress")
    assert denied["success"] is False
    assert "operator" in denied["error"].lower()


def test_coding_may_only_set_in_review(skill: CardSkill):
    skill.set_card_status(card_id="CARD-300", status="Ready")
    skill.set_card_status(card_id="CARD-300", status="In Progress")
    token = _tool_context.set({"agent_id": "coding"})
    try:
        deny_done = skill.set_card_status(card_id="CARD-300", status="Done")
        assert deny_done["success"] is False
        assert "In Progress -> In Review only" in deny_done["error"]
        ok = skill.set_card_status(card_id="CARD-300", status="In Review")
        assert ok["success"] is True
        assert ok["status"] == "In Review"
        deny_returned = skill.set_card_status(card_id="CARD-300", status="Returned", return_reason="x")
        assert deny_returned["success"] is False
    finally:
        _tool_context.reset(token)
