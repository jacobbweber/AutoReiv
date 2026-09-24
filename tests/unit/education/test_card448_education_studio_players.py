"""CARD-448: Studio players use durable Learning OS grade / due / next APIs.

REQ-448-002/003: player grade path is POST /api/education/quiz/grade;
failures do not fabricate correct=true; Education tab retained.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.application.education.quiz_engine import grade_answer_binary
from src.infrastructure.memory.repositories.agent_memory import AgentMemoryRepository


def _repo(tmp_path: Path) -> AgentMemoryRepository:
    db = tmp_path / "tutor_memory.db"
    repo = AgentMemoryRepository(db_path=db)
    repo.initialize_schema()
    return repo


def test_player_grade_path_persists_and_survives_reload(tmp_path: Path):
    """[REQ-448-002][REQ-448-003] Durable mastery row after grade; reload sees it."""
    repo = _repo(tmp_path)
    mid = repo.upsert_education_mastery(
        item_id="edu_card448_player",
        topic="CARD-448 Players",
        wiki_path="01_Notes/card448.md",
        prompt="What API do Studio players grade through?",
        expected_answer="POST /api/education/quiz/grade",
        grade="unseen",
    )
    now = datetime(2026, 9, 24, 4, 0, 0, tzinfo=timezone.utc)
    row = repo.record_education_grade(item_id=mid, correct=True, now=now)
    assert row["grade"] == "pass"
    assert row.get("next_due")

    repo2 = AgentMemoryRepository(db_path=tmp_path / "tutor_memory.db")
    repo2.initialize_schema()
    loaded = repo2.get_education_mastery(mid)
    assert loaded is not None
    assert loaded["grade"] == "pass"
    assert loaded.get("next_due")
    assert any(r["item_id"] == mid for r in repo2.list_education_mastery())


def test_player_miss_is_honest_binary():
    """[REQ-448-002] Miss answers do not equal expected — no fake pass."""
    assert grade_answer_binary("POST /api/education/quiz/grade", "") is False
    assert grade_answer_binary("POST /api/education/quiz/grade", "ephemeral score") is False
    assert (
        grade_answer_binary(
            "POST /api/education/quiz/grade", "POST /api/education/quiz/grade"
        )
        is True
    )


def test_card448_players_module_and_console_exist():
    """[REQ-448-001][REQ-448-005] Players module + console + Education tab present."""
    root = Path(__file__).resolve().parents[3]
    players = (root / "src/web/static/modules/studios/education_players.js").read_text(
        encoding="utf-8"
    )
    html = (root / "src/web/templates/index.html").read_text(encoding="utf-8")
    assert "initEducationStudioPlayers" in players
    assert "/api/education/quiz/grade" in players
    assert "fake_pass: false" in players
    assert 'id="educationPlayersConsole"' in html
    assert 'id="tab-education"' in html
    assert 'id="tab-lumina"' in html
    assert 'id="educationOperatorConsole"' in html
