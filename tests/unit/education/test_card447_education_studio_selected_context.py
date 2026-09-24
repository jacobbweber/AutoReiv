"""CARD-447: Education Studio selected topic/course (Projects parallel).

Durable settings key selected_education_context + GET/PUT /api/education/selected.
Tutor/Study entry injects this context. Does not implement CARD-448 players.
"""

from __future__ import annotations

from pathlib import Path

from src.application.education.selected_context import (
    SELECTED_EDUCATION_CONTEXT_KEY,
    get_selected_education_context,
    set_selected_education_context,
)
from src.infrastructure.memory.sqlite_store import SQLiteStateStore


def _store() -> SQLiteStateStore:
    store = SQLiteStateStore(db_path=":memory:")
    store.initialize_db()
    return store


def test_selected_education_context_persists_and_survives_reread():
    store = _store()
    assert get_selected_education_context(store) == {}
    res = set_selected_education_context(
        store, topic="Bayes Theorem", course_id="course_abc", agent_id="tutor"
    )
    assert res["success"] is True
    assert res["selected"]["topic"] == "Bayes Theorem"
    assert res["selected"]["course_id"] == "course_abc"
    assert res["selected"]["agent_id"] == "tutor"
    assert res["selected"]["source"] == "education_studio"
    assert res["selected"]["updated_at"]
    again = get_selected_education_context(store)
    assert again["topic"] == "Bayes Theorem"
    assert again["course_id"] == "course_abc"
    raw = store.get_setting(SELECTED_EDUCATION_CONTEXT_KEY)
    assert isinstance(raw, dict)
    assert raw["topic"] == "Bayes Theorem"


def test_selected_education_context_requires_topic_and_clears():
    store = _store()
    failed = set_selected_education_context(store, topic="  ")
    assert failed["success"] is False
    assert "topic" in (failed.get("error") or "").lower()
    set_selected_education_context(store, topic="Raft")
    cleared = set_selected_education_context(store, clear=True)
    assert cleared["success"] is True
    assert cleared["selected"] == {}
    assert get_selected_education_context(store) == {}


def test_education_selected_routes_exist_in_router_source():
    text = Path("src/web/routers/education.py").read_text(encoding="utf-8")
    assert 'GET /api/education/selected' in text or '"/api/education/selected"' in text
    assert "get_selected_education_context_api" in text
    assert "put_selected_education_context_api" in text
    assert "SelectedEducationContextPayload" in text
    assert "projects_parallel" in text
